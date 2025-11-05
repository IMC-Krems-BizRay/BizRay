from zeep import Client
from zeep.transports import Transport
from requests import Session
from .config import API_KEY, WSDL_URL

def create_client():
    session = Session()
    session.headers.update({'X-API-KEY': f'{API_KEY}', 'Content-Type': 'application/soap+xml;charset=UTF-8'})
    transport = Transport(session=session)
    client = Client(wsdl=WSDL_URL, transport=transport)
    for service in client.wsdl.services.values():
        for port in service.ports.values():
            port.binding_options['address'] = "https://justizonline.gv.at/jop/api/at.gv.justiz.fbw/ws"

    return client


if __name__ == "__main__":
    c = create_client()
    for service in c.wsdl.services.values():
        for port in service.ports.values():
            print(f"  Port: {port.name}")
            print(f"  Address: {port.binding_options['address']}")
            operations = port.binding._operations
            for operation in operations.values():
                print(f"Method: {operation.name}")
                print(f"Input: {operation.input.signature()}")
                print(f"Output: {operation.output.signature()}")
                print("-" * 40)



