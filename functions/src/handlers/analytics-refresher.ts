// λ analytics-refresher: recalcula con Athena los agregados diarios del tablero y los deja en
// DynamoDB, que es de donde lee el panel. La dispara EventBridge con dos reglas:
//
//   - cada pocos minutos, la vuelta corta (`recent`): solo los últimos días. Son los únicos que
//     cambian, porque el lake solo agrega archivos y una visita cae en el día en que terminó;
//   - una vez por día, la vuelta completa (`full`): toda la ventana del tablero. Corrige lo que haya
//     llegado tarde o repetido a un día viejo.
//
// Recalcular solo dos días en lugar de noventa baja lo que Athena escanea y lo que se escribe en
// DynamoDB en un 97 %. Cada vuelta recalcula sus días desde el lake, sin sumar sobre lo anterior: no
// hay estado incremental que se pueda desfasar, y dos ejecuciones superpuestas escriben lo mismo.
//
// El historial de demo carga días viejos: deja un pedido de recálculo completo (`fullRefreshRequested`)
// y, mientras está vigente, las vueltas cortas también recalculan la ventana entera.

import { AthenaClient, GetQueryExecutionCommand, GetQueryResultsCommand, StartQueryExecutionCommand } from '@aws-sdk/client-athena'
import type { GetQueryExecutionCommandOutput, GetQueryResultsCommandOutput } from '@aws-sdk/client-athena'
import { aggregatesQuery, parseRows } from '../analytics/aggregates.js'
import type { DailyAggregate } from '../analytics/aggregates.js'
import { addDays } from '../analytics/dashboard.js'
import { required } from '../consumers/sqs.js'
import { AnalyticsStore } from '../persistence/analytics-store.js'
import { createTableConfig } from '../persistence/client.js'

type AthenaCommand = StartQueryExecutionCommand | GetQueryExecutionCommand | GetQueryResultsCommand

export interface RefresherDependencies {
  athena: { send(command: AthenaCommand): Promise<unknown> }
  store: {
    putDays(days: readonly DailyAggregate[], refreshedAt: Date): Promise<void>
    fullRefreshRequested(now: Date): Promise<boolean>
  }
  workgroup: string
  database: string
  table: string
  /** Cuántos días hacia atrás recalcula la vuelta completa: los del rango más largo del tablero. */
  windowDays: number
  now?: () => Date
  pause?: (milliseconds: number) => Promise<void>
}

/**
 * Cuántos días hacia atrás recalcula la vuelta corta. Hoy y ayer del local, más uno de margen: el día
 * se toma en UTC, y para un local al oeste de UTC el día local puede ser el anterior.
 */
export const RECENT_DAYS = 2

/** `recent`: los últimos días, cada pocos minutos. `full`: la ventana entera, una vez por día. */
export type RefreshWindow = 'recent' | 'full'

const POLL_MILLISECONDS = 1000
const sleep = (milliseconds: number) => new Promise<void>((resolve) => setTimeout(resolve, milliseconds))

export interface RefreshResult {
  window: RefreshWindow
  queryExecutionId: string
  since: string
  days: number
  /** Lo que escaneó Athena: lo que se paga. */
  bytesScanned: number
}

export async function refresh(
  deps: RefresherDependencies,
  deadline: () => number = () => Infinity,
  requested: RefreshWindow = 'full',
): Promise<RefreshResult> {
  const now = deps.now?.() ?? new Date()
  const pause = deps.pause ?? sleep
  const window: RefreshWindow = requested === 'full' || (await deps.store.fullRefreshRequested(now)) ? 'full' : 'recent'
  // Un día de margen: el día local de un local al oeste de UTC puede ser el anterior al de UTC.
  const since = addDays(now.toISOString().slice(0, 10), -(window === 'full' ? deps.windowDays : RECENT_DAYS))

  const started = (await deps.athena.send(
    new StartQueryExecutionCommand({
      QueryString: aggregatesQuery(deps.database, deps.table, since),
      WorkGroup: deps.workgroup,
      QueryExecutionContext: { Database: deps.database },
    }),
  )) as { QueryExecutionId?: string }
  const queryExecutionId = started.QueryExecutionId
  if (!queryExecutionId) throw new Error('Athena no devolvió el id de la consulta')

  // Athena es asíncrona: se arranca la consulta y se pregunta hasta que termina.
  let execution: GetQueryExecutionCommandOutput['QueryExecution']
  for (;;) {
    const result = (await deps.athena.send(new GetQueryExecutionCommand({ QueryExecutionId: queryExecutionId }))) as GetQueryExecutionCommandOutput
    execution = result.QueryExecution
    const state = execution?.Status?.State
    if (state === 'SUCCEEDED') break
    if (state === 'FAILED' || state === 'CANCELLED') {
      throw new Error(`La consulta ${queryExecutionId} terminó ${state}: ${execution?.Status?.StateChangeReason ?? ''}`)
    }
    if (deadline() < POLL_MILLISECONDS * 3) throw new Error(`La consulta ${queryExecutionId} no terminó a tiempo`)
    await pause(POLL_MILLISECONDS)
  }

  const rows: (string | undefined)[][] = []
  let nextToken: string | undefined
  do {
    const page = (await deps.athena.send(
      new GetQueryResultsCommand({ QueryExecutionId: queryExecutionId, NextToken: nextToken, MaxResults: 1000 }),
    )) as GetQueryResultsCommandOutput
    for (const row of page.ResultSet?.Rows ?? []) rows.push((row.Data ?? []).map((datum) => datum.VarCharValue))
    nextToken = page.NextToken
  } while (nextToken)

  const days = parseRows(rows)
  await deps.store.putDays(days, now)
  return {
    window,
    queryExecutionId,
    since,
    days: days.length,
    bytesScanned: execution?.Statistics?.DataScannedInBytes ?? 0,
  }
}

let deps: RefresherDependencies | undefined

/** Lo que manda EventBridge en cada regla. Invocada a mano, sin `window`, recalcula todo. */
export interface RefreshEvent {
  window?: RefreshWindow
}

export const handler = async (event: RefreshEvent | null | undefined, context?: { getRemainingTimeInMillis?: () => number }): Promise<RefreshResult> => {
  deps ??= {
    athena: new AthenaClient({}),
    store: new AnalyticsStore(createTableConfig()),
    workgroup: required('ATHENA_WORKGROUP'),
    database: required('GLUE_DATABASE'),
    table: required('GLUE_TABLE'),
    windowDays: Number(required('WINDOW_DAYS')),
  }
  const window: RefreshWindow = event?.window === 'recent' ? 'recent' : 'full'
  const result = await refresh(deps, () => context?.getRemainingTimeInMillis?.() ?? Infinity, window)
  console.log('Agregados recalculados', JSON.stringify(result))
  return result
}
