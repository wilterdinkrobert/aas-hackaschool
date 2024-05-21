import base64


def base64encode(data: str) -> str:
    return str(base64.b64encode(data.encode('utf-8')), "utf-8")
