import asyncio

async def test():
    reader, writer = await asyncio.open_connection('localhost', 8765)
    print('Connected')
    
    # Send initialize request
    request = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "test", "version": "0.1.0"}}}\n'
    writer.write(request.encode())
    await writer.drain()
    
    # Read response
    line = await reader.readline()
    print('Response:', line.decode())
    
    writer.close()
    await writer.wait_closed()

asyncio.run(test())