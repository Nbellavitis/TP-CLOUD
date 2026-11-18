# Las alarmas de todo el sistema avisan acá. Con `alert_email`, además llegan por email (hay que
# confirmar la suscripción desde el link que manda AWS).

# Sin cifrado, a propósito: las alarmas de CloudWatch no pueden publicar en un tópico cifrado con la
# clave que administra AWS; haría falta una clave KMS propia con su política. Solo lleva avisos de
# alarmas, sin datos de los clientes.
#tfsec:ignore:aws-sns-enable-topic-encryption
resource "aws_sns_topic" "alerts" {
  name = format("%s-alerts", var.project)
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count = var.alert_email == null ? 0 : 1

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Lo que falla sin pasar por una DLQ. Las alarmas de las colas (módulo queue-with-dlq) y la de
# q-stream-failures avisan cuando un mensaje agotó sus reintentos; estas cubren los caminos que no
# tienen una cola donde caer: un stream que se atrasa, el tablero que deja de recalcularse y el lake
# que deja de recibir datos. Las tres sin datos son "todo bien": sin tráfico no hay métrica.

# El stream se atrasa: stream-publisher no da abasto o está estrangulado. q-stream-failures recibe un
# registro recién cuando agota sus reintentos, o cuando lleva una hora sin poder procesarse; esto avisa
# antes. Tres minutos seguidos, para no avisar en cada despliegue: al crearse, el mapping arranca desde
# el registro más viejo (TRIM_HORIZON) y se pone al día en la primera vuelta.
resource "aws_cloudwatch_metric_alarm" "stream_lag" {
  alarm_name          = format("%s-stream-lag", var.project)
  alarm_description   = "Los eventos de q-main esperan más de un minuto en el stream: stream-publisher no da abasto o está estrangulado."
  namespace           = "AWS/Lambda"
  metric_name         = "IteratorAge"
  dimensions          = { FunctionName = module.workers["stream-publisher"].name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  datapoints_to_alarm = 3
  comparison_operator = "GreaterThanThreshold"
  threshold           = 60000
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# El tablero de análisis se congela: el refresher falla y el panel sigue mostrando los últimos
# agregados que guardó, sin ningún error a la vista. Dos vueltas seguidas con error, porque una sola
# puede ser pasajera y la vuelta siguiente recalcula todo igual.
resource "aws_cloudwatch_metric_alarm" "analytics_refresh_errors" {
  alarm_name          = format("%s-analytics-refresh-errors", var.project)
  alarm_description   = "El recálculo del tablero de análisis falló dos vueltas seguidas: el panel muestra datos viejos."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = module.workers["analytics-refresher"].name }
  statistic           = "Sum"
  period              = var.analytics_refresh_minutes * 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# Firehose no pudo convertir visitas a Parquet: van a errores/ en el lake y no aparecen en Athena. Pasa
# si la fila deja de coincidir con el esquema de la tabla de Glue.
resource "aws_cloudwatch_metric_alarm" "lake_conversion_failures" {
  alarm_name          = format("%s-lake-conversion-failures", var.project)
  alarm_description   = "Firehose no pudo convertir visitas a Parquet: quedaron en errores/ del lake y no llegan al tablero."
  namespace           = "AWS/Firehose"
  metric_name         = "FailedConversion.Records"
  dimensions          = { DeliveryStreamName = aws_kinesis_firehose_delivery_stream.visits.name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# Firehose no pudo escribir en el bucket del lake (un permiso o el bucket borrado). Reintenta durante
# un día y después manda los registros a errores/.
resource "aws_cloudwatch_metric_alarm" "lake_delivery_failures" {
  alarm_name          = format("%s-lake-delivery-failures", var.project)
  alarm_description   = "Firehose no pudo escribir en el bucket del lake: las visitas no llegan a Athena."
  namespace           = "AWS/Firehose"
  metric_name         = "DeliveryToS3.Success"
  dimensions          = { DeliveryStreamName = aws_kinesis_firehose_delivery_stream.visits.name }
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}
