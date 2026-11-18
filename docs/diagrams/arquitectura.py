# -*- coding: utf-8 -*-
"""
Diagrama de arquitectura de Queue (TP4), con la convención de AWS: AWS Cloud, la región y los
servicios conectados entre sí. Lo de afuera de AWS (el navegador, GitHub Actions, Gmail) queda
afuera del borde. Cada nodo es un recurso del Terraform de terraform/organization.

    python3 docs/diagrams/arquitectura.py      # escribe arquitectura.svg al lado de este archivo
    node docs/diagrams/render.mjs              # y lo exporta a arquitectura.png
"""
import json
import os

OUT = os.path.dirname(os.path.abspath(__file__))

INK = "#232f3e"
MUTED = "#5a6b73"
CLOUD = "#232f3e"
REGION = "#00a4a6"
REQ = "#6b4fbb"     # pedidos del navegador
SYNC = "#0f7a72"    # escrituras y lecturas de datos
BUS = "#c7511f"     # eventos y colas
OPS = "#3b4a54"     # despliegue y operación
ALERT = "#b0202f"
FONT = "DejaVu Sans, Verdana, Geneva, sans-serif"

W, H = 2000, 2010
ICON = 64
TITLE = 20     # nombre de cada servicio
SUB = 15       # su detalle
CHIP = 14      # etiquetas de las flechas


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self, icons):
        self.icons = icons
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def box(self, x, y, w, h, stroke, fill="none", dash=None, width=2):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" '
                 f'stroke-width="{width}"{d}/>')

    def text(self, x, y, t, size=13, fill=INK, anchor="start", weight="normal"):
        self.add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}">{esc(t)}</text>')

    def group(self, x, y, w, h, color, label, icon=None, dash=None, fill="none"):
        """Un grupo de AWS: borde, ícono en la esquina y el nombre al lado."""
        self.box(x, y, w, h, color, fill, dash)
        if icon:
            self.add(f'<rect x="{x}" y="{y}" width="36" height="36" fill="{color}"/>')
            self.add(f'<g transform="translate({-0.2 * x:.1f} {-0.2 * y:.1f}) scale(1.2)">{icon(x, y)}</g>')
        self.text(x + (46 if icon else 12), y + 25, label, 18, color, weight="bold")

    def node(self, key, cx, cy, title, *lines, color=INK):
        """Un servicio: el ícono centrado en (cx, cy), su nombre debajo (una o dos líneas) y el detalle."""
        self.add(f'<image href="{self.icons[key]}" x="{cx - ICON / 2}" y="{cy - ICON / 2}" '
                 f'width="{ICON}" height="{ICON}"/>')
        y = cy + ICON / 2 + 23
        for part in title.split("\n"):
            self.text(cx, y, part, TITLE, color, anchor="middle", weight="bold")
            y += TITLE + 4
        for line in lines:
            self.text(cx, y, line, SUB, MUTED, anchor="middle")
            y += SUB + 4

    def mail(self, cx, cy, title, *lines):
        """Un buzón de email externo (no es un servicio de AWS, así que no lleva ícono de AWS)."""
        x, y = cx - 32, cy - 22
        self.add(f'<rect x="{x}" y="{y}" width="64" height="44" rx="5" fill="#ffffff" stroke="{INK}" '
                 f'stroke-width="2.5"/><path d="M{x} {y} L{cx} {cy + 6} L{x + 64} {y}" fill="none" '
                 f'stroke="{INK}" stroke-width="2.5"/>')
        y = cy + 22 + 25
        for part in title.split("\n"):
            self.text(cx, y, part, TITLE, INK, anchor="middle", weight="bold")
            y += TITLE + 4
        for line in lines:
            self.text(cx, y, line, SUB, MUTED, anchor="middle")
            y += SUB + 4

    def line(self, points, color, dash=None, arrow=True, width=2.4):
        d = "M" + " L".join(f"{x} {y}" for x, y in points)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#m{color[1:]})"' if arrow else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{da}{m}/>')

    def chip(self, x, y, t, color, size=CHIP):
        w = len(t) * size * 0.6 + 14
        self.add(f'<rect x="{x - w / 2:.0f}" y="{y - size - 3}" width="{w:.0f}" height="{size + 9}" '
                 f'rx="5" fill="#ffffff" stroke="{color}" stroke-width="1.3"/>')
        self.text(x, y, t, size, color, anchor="middle", weight="bold")

    def render(self):
        markers = "".join(
            f'<marker id="m{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
            f'markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for c in (REQ, SYNC, BUS, OPS, ALERT, INK)
        )
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
                f'role="img" aria-label="Arquitectura de Queue en AWS">'
                f'<defs>{markers}</defs><rect width="{W}" height="{H}" fill="#ffffff"/>')
        return head + "".join(self.parts) + "</svg>"


def cloud_icon(x, y):
    return (f'<path d="M{x + 8} {y + 21} a5 5 0 0 1 1-10 a7 7 0 0 1 13-1 a5 5 0 0 1 2 11 z" '
            f'fill="none" stroke="#ffffff" stroke-width="1.8"/>')


def region_icon(x, y):
    return (f'<path d="M{x + 15} {y + 5} a6 6 0 0 1 6 6 c0 5 -6 13 -6 13 c0 0 -6 -8 -6 -13 a6 6 0 0 1 6 -6 z" '
            f'fill="none" stroke="#ffffff" stroke-width="1.8"/><circle cx="{x + 15}" cy="{y + 11}" r="2" fill="#ffffff"/>')


def build(icons):
    s = Svg(icons)
    h = ICON / 2

    # columnas y filas de la grilla. c0 es el borde (WAF); c7, el tercer consumidor de SNS.
    c0, c1, c2, c3, c4, c5, c6, c7 = 315, 450, 655, 860, 1065, 1270, 1475, 1680
    rA, rB, rC, rE, rH, rI, rF, rG = 255, 470, 680, 885, 1190, 1395, 1610, 1780
    ext_l, ext_r = 110, 1905

    s.text(30, 46, "Queue · arquitectura en AWS (TP4)", 30, weight="bold")
    s.text(30, 76, "Serverless · desplegada con Terraform desde GitHub Actions · AWS Academy Learner Lab · Grupo 9",
           16, MUTED)

    # ------------------------------------------------------------ leyenda, en una fila
    legend = [(REQ, "pedido del usuario"), (SYNC, "datos"), (BUS, "evento o mensaje"), (ALERT, "alarma"),
              (OPS, "pipeline e infraestructura")]
    lx = 30
    for color, label in legend:
        s.line([(lx, 108), (lx + 40, 108)], color)
        s.text(lx + 50, 113, label, 15, INK)
        lx += 50 + len(label) * 8.6 + 40

    # ------------------------------------------------------------ bordes
    s.group(220, 135, 1590, 1795, CLOUD, "AWS Cloud", icon=cloud_icon)
    s.group(245, 185, 1540, 1720, REGION, "Región us-east-1  ·  sin VPC", icon=region_icon, dash="9 6")
    s.box(c2 - 120, rH - 80, c6 - c2 + 245, rI - rH + 215, SYNC, "#f3faf9", "6 5", 1.6)
    s.text(c2 - 108, rH - 54, "Analítica · data lake", 18, SYNC, weight="bold")

    # ------------------------------------------------------------ afuera de AWS
    s.node("user", ext_l, rB, "Navegador", "cliente y staff")
    s.node("gha", ext_l, rF, "GitHub\nActions", "el pipeline", color=OPS)
    s.node("tf", ext_l, rG, "Terraform", "crea y configura todo", color=OPS)
    s.mail(ext_r, rE, "Gmail\nSMTP", "mails a clientes")
    s.mail(ext_r, rG, "Mail del\nequipo", "alarmas")

    # ------------------------------------------------------------ entrada, API y datos
    s.node("waf", c0, rB, "WAF", "tope por IP")
    s.node("cognito", c1, rA, "Cognito", "staff · SRP")
    s.node("lambda", c3, rA, "λ seed", "demo e historial")
    s.node("apigw", c1, rB, "API Gateway\nREST", "sitio + /api/v1")
    s.node("lambda", c2, rB, "λ staff", "panel y llamados")
    s.node("ddb", c3, rB, "DynamoDB\nq-main", "tabla única")
    s.node("s3", c1, rC, "S3 spa", "lo sube Terraform")
    s.node("lambda", c2, rC, "λ public", "anotarse y ticket")
    s.node("apigw", c1, rE, "API Gateway\nWebSocket", "tiempo real")
    s.node("lambda", c2, rE, "λ ws-connections", "abre y cierra")
    s.node("ddb", c3, rE, "DynamoDB\nq-connections", "sockets abiertos")

    # ------------------------------------------------------------ bus de eventos
    s.node("ddbstream", c4, rB, "DynamoDB\nStreams")
    s.node("lambda", c5, rB, "λ stream-publisher")
    s.node("sns", c6, rB, "SNS FIFO", "q-queue-events")
    s.node("sqs", c4, rC, "SQS\nq-lifecycle", "demora = gracia")
    s.node("sqs", c5, rC, "SQS FIFO\nq-push", "orden por cola")
    s.node("sqs", c6, rC, "SQS\nq-analytics", "fin de visita")
    s.node("sqs", c7, rC, "SQS\nq-notifications", "filtro por tipo")
    s.node("lambda", c4, rE, "λ lifecycle", "escribe en q-main")
    s.node("lambda", c5, rE, "λ broadcaster", "lee q-main")
    s.node("lambda", c6, rE, "λ archiver", "lee q-main")
    s.node("lambda", c7, rE, "λ notifier", "escribe en q-main")

    # ------------------------------------------------------------ analítica
    s.node("eventbridge", c2, rH, "EventBridge", "cada 5 min y diaria")
    s.node("lambda", c3, rH, "λ analytics-\nrefresher", "guarda en q-main")
    s.node("athena", c4, rH, "Athena", "tope de 1 GB")
    s.node("s3", c5, rH, "S3 lake", "Parquet por día")
    s.node("firehose", c6, rH, "Data\nFirehose", "JSON a Parquet")
    s.node("s3", c4, rI, "S3 athena", "resultados")
    s.node("glue", c5, rI, "Glue Data\nCatalog", "esquema, sin crawler")

    # ------------------------------------------------------------ transversales
    s.node("iam", c2, rF, "IAM LabRole", "rol de todo", color=OPS)
    s.node("cw", c3, rF, "CloudWatch\nLogs", "logs de las λ", color=OPS)
    s.node("secrets", c7, rF, "Secrets\nManager", "credencial SMTP")
    s.node("s3", c1, rG, "S3 artifacts", "código de las λ", color=OPS)
    s.node("s3", c2, rG, "S3 logs", "access logs", color=OPS)
    s.node("s3", c3, rG, "S3 tfstate", "estado", color=OPS)
    s.node("sqs", c4, rG, "SQS DLQs", "mensajes fallidos", color=ALERT)
    s.node("cw", c5, rG, "CloudWatch\nAlarms", color=ALERT)
    s.node("sns", c6, rG, "SNS q-alerts", color=ALERT)

    # ------------------------------------------------------------ pedidos del usuario
    s.line([(ext_l + h, rB - 14), (c1 - h, rA + 12)], REQ)
    s.chip(280, 365, "login", REQ)
    s.line([(ext_l + h, rB), (c0 - h, rB)], REQ)
    s.chip(222, rB - 6, "HTTPS", REQ)
    s.line([(c0 + h, rB), (c1 - h, rB)], REQ)
    s.line([(ext_l + h, rB + 14), (200, rB + 14), (c1 - h, rE - 12)], REQ)
    s.chip(300, 690, "wss", REQ)
    s.line([(c1, rB - h), (c1, rA + h + 58)], REQ)
    s.chip(c1, 375, "valida el token", REQ)
    s.line([(c2 - h + 4, rB - h), (c1 + h, rA + 18)], REQ)
    s.chip(602, 412, "alta de miembros", REQ)
    s.line([(c1 + h, rB), (c2 - h, rB)], REQ)
    s.line([(c1 + h, rB + 14), (c2 - h, rC - 10)], REQ)
    s.line([(c1, rB + h + 84), (c1, rC - h)], REQ)
    s.line([(c1 + h, rE), (c2 - h, rE)], REQ)

    # ------------------------------------------------------------ datos
    s.line([(c2 + h, rB), (c3 - h, rB)], SYNC)
    s.line([(c2 + h, rC - 10), (c3 - h, rB + 14)], SYNC)
    s.line([(c3, rA + h + 58), (c3, rB - h)], SYNC)
    s.line([(c2 + h, rE), (c3 - h, rE)], SYNC)

    # ------------------------------------------------------------ eventos
    s.line([(c3 + h, rB), (c4 - h, rB)], BUS)
    s.line([(c4 + h, rB), (c5 - h, rB)], BUS)
    s.line([(c5 + h, rB), (c6 - h, rB)], BUS)
    s.line([(c5 - 10, rB + h + 32), (c4 + h, rC - h)], BUS)
    s.chip(1160, 595, "llamados y cierres", BUS)
    s.line([(c6 - 10, rB + h + 70), (c5 + h, rC - h)], BUS)
    s.line([(c6, rB + h + 70), (c6, rC - h)], BUS)
    s.line([(c6 + 10, rB + h + 70), (c7 - h, rC - h)], BUS)
    for c in (c4, c5, c6, c7):
        s.line([(c, rC + h + 80), (c, rE - h)], BUS)

    # lifecycle se reprograma si la gracia supera los 15 minutos de demora de SQS
    s.line([(c4 - h, rE - 10), (c4 - 80, rE - 10), (c4 - 80, rC + 10), (c4 - h, rC + 10)], BUS)
    s.chip(c4 - 80, 832, "reprograma", BUS)

    # broadcaster: lee las conexiones y empuja por el WebSocket
    s.line([(c5, rE + h + 70), (c5, 1010), (c3, 1010), (c3, rE + h + 74)], SYNC)
    s.line([(c5 - 20, rE + h + 70), (c5 - 20, 1040), (275, 1040), (275, rE + 12), (c1 - h, rE + 12)], BUS)
    s.chip(760, 1032, "push al navegador", BUS)

    # notifier
    s.line([(c7, rE + h + 70), (c7, rF - h)], SYNC)
    s.line([(c7 + h, rE), (ext_r - 32, rE)], BUS)

    # analítica: el archiver carga el lake; EventBridge dispara el recálculo con Athena
    s.line([(c6, rE + h + 70), (c6, rH - h)], SYNC)
    s.chip(c6, 1085, "una fila por visita", SYNC)
    s.line([(c6 - h, rH), (c5 + h, rH)], SYNC)
    s.chip(1372, rH - 8, "Parquet", SYNC)
    s.line([(c2 + h, rH), (c3 - h, rH)], BUS)
    s.line([(c3 + h, rH), (c4 - h, rH)], SYNC)
    s.chip(962, rH - 8, "SQL", SYNC)
    s.line([(c4 + h, rH), (c5 - h, rH)], SYNC)
    s.line([(c4, rH + h + 75), (c4, rI - h)], SYNC)
    s.line([(c6 - 24, rH + h + 98), (c5 + h, rI - 12)], SYNC, dash="7 5")
    s.chip(1395, 1352, "esquema", SYNC)
    s.line([(c4 + 24, rH + h + 75), (c5 - h, rI - 12)], SYNC, dash="7 5")

    # alarmas
    s.line([(c4 + h, rG), (c5 - h, rG)], ALERT)
    s.line([(c5 + h, rG), (c6 - h, rG)], ALERT)
    s.line([(c6 + h, rG), (ext_r - 32, rG)], ALERT)

    # infraestructura: el pipeline crea los buckets y corre Terraform, que sube el código de las λ
    s.line([(ext_l + h, rF), (245, rF)], OPS)
    s.chip(178, rF - 8, "buckets", OPS)
    s.line([(ext_l, rF + h + 70), (ext_l, rG - h)], OPS)
    s.line([(ext_l + h, rG), (c1 - h, rG)], OPS)
    s.chip(280, rG - 8, "sube el código", OPS)

    # ------------------------------------------------------------ notas
    notes = [
        "Sin VPC: todos los servicios son regionales y administrados por AWS; las funciones los usan por HTTPS, con el rol LabRole.",
        "Los 5 buckets de la app los crea el pipeline con la CLI (un SCP del lab bloquea aws_s3_bucket); Terraform configura todo lo demás.",
    ]
    for i, n in enumerate(notes):
        s.text(30, 1965 + 24 * i, n, 15, MUTED)
    return s.render()


def main():
    with open(os.path.join(OUT, "icons.json")) as f:
        icons = json.load(f)
    path = os.path.join(OUT, "arquitectura.svg")
    with open(path, "w") as f:
        f.write(build(icons))
    print(path)


if __name__ == "__main__":
    main()
