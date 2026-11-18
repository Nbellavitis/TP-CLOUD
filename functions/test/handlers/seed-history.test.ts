import type { PutRecordBatchCommand } from '@aws-sdk/client-firehose'
import { describe, expect, it } from 'vitest'
import { HISTORY_FULL_REFRESH_MINUTES, seedHistory } from '../../src/handlers/seed.js'

describe('seedHistory', () => {
  it('después de cargar el historial pide un recálculo completo del tablero', async () => {
    const sent: number[] = []
    const requested: Date[] = []
    const now = new Date('2026-03-02T15:00:00.000Z')
    const result = await seedHistory(
      {
        establishment: { id: 'est-1', name: 'Demo', timezone: 'America/Argentina/Buenos_Aires' },
        queues: [{ id: 'q1', defaultLaneId: 'l1', settings: { name: 'Mesas' } }],
        days: 3,
      },
      {
        firehose: {
          async send(command: PutRecordBatchCommand) {
            const records = command.input.Records ?? []
            sent.push(records.length)
            return { RequestResponses: records.map(() => ({ RecordId: 'r' })) }
          },
        },
        deliveryStreamName: 'q-visitas',
        pause: async () => {},
        analytics: {
          async requestFullRefresh(until) {
            requested.push(until)
          },
        },
      },
      now,
    )
    expect(result.visits).toBe(sent.reduce((sum, count) => sum + count, 0))
    expect(requested).toEqual([new Date(now.getTime() + HISTORY_FULL_REFRESH_MINUTES * 60_000)])
  })
})
