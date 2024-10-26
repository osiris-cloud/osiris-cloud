import httpx
from json import dumps as json_dumps

from core.settings import env


# https://app.swaggerhub.com/apis-docs/ADMIN_111/loxilb/1.0.0

def add_lb_rule(ext_port: int, endpoints: list[str], dst_port: int, proto: str = "tcp") -> bool:
    request = json_dumps({
        "serviceArguments": {
            "externalIP": "0.0.0.0",
            "port": ext_port,
            "protocol": proto,
            "sel": 3,
            "bgp": False,
            "monitor": True,
            "mode": 1,
            "inactiveTimeOut": 0,
        },
        "endpoints": [
            {
                "endpointIP": ep,
                "weight": 1,
                "targetPort": dst_port,
                "state": "active",
            } for ep in endpoints
        ]
    })

    with httpx.Client(base_url=env.firewall_url + '/netlox/v1/config') as client:
        r = client.post('/loadbalancer', json=request)

    return r.status_code == 200


def delete_lb_rule(ext_port: str, endpoints: list[str]) -> bool:
    with httpx.Client(base_url=env.firewall_url + '/netlox/v1/config') as client:

        r = client.delete(f'/loadbalancer/externalipaddress/0.0.0.0/port/{ext_port}/protocol/tcp')

    return r.status_code == 200


def add_ingress_rule(namespace: str, service: str, port: int, proto: str = "tcp") -> bool:
    pass


def delete_ingress_rule(namespace: str, service: str, port: int, proto: str = "tcp") -> bool:
    pass
