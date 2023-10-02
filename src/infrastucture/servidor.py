import asyncio


HOST, PORT = 'localhost', 111

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           
async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')

    print(f'Cliente conectado: {addr}')
    while True:
        data = await reader.read(100)
        message = data.decode()
        if message == "":
            break
        print(f"Recibido: {message} de {addr}")
        response = f"Servidor: He recibido tu mensaje: '{message}'"
        print(f"Enviando: {response} a {addr}")
        writer.write(response.encode())
        await writer.drain()

    print(f'Cliente desconectado: {addr}')
    writer.close()
    await writer.wait_closed()

async def start_server():
    server = await asyncio.start_server(
        handle_client,
        HOST, PORT)

    addr = server.sockets[0].getsockname()
    print(f'Servidor iniciado en {addr}')

    
    print('GPIOS Configurados')

    async with server:
        await server.serve_forever()
    

asyncio.run(start_server())