import asyncio
import sys
import os
import json
os.environ['RHINO_MCP_USE_HTTP'] = '1'
os.environ['RHINO_MCP_HTTP_URL'] = 'http://localhost:8765'
sys.path.insert(0, r'E:\Rhino AI_R1\AI-RHINO-ARCHITECT')

from rhino.adapters.mcp import MCPRhinoAdapter
from apps.api.mcp.config import RhinoMCPConfig

async def test_live():
    config = RhinoMCPConfig()
    adapter = MCPRhinoAdapter(config)
    await adapter._client.connect()
    print('Connected to Rhino MCP server')
    
    # Create a rectangle first
    result = await adapter.call_tool('run_python', {
        'script': '''
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
plane = rg.Plane.WorldXY
rect = rg.Rectangle3d(plane, rg.Interval(0, 5000), rg.Interval(0, 3000))
guid = rs.AddPolyline(rect.ToPolyline())
print(json.dumps({"guid": str(guid)}))
'''
    })
    outer = json.loads(result['content'][0]['text'])
    stdout = outer.get('stdout', '{}')
    inner = json.loads(stdout)
    rect_guid = inner.get('guid')
    print(f'Rectangle: {rect_guid}')
    
    # Create ridge line
    result = await adapter.call_tool('run_python', {
        'script': f'''
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
boundary = rs.coercecurve("{rect_guid}")
bbox = boundary.GetBoundingBox(True)
min_pt = bbox.Min
max_pt = bbox.Max
cx = (min_pt.X + max_pt.X) / 2
cy = (min_pt.Y + max_pt.Y) / 2
ridge_height = 1000
ridge_start = (min_pt.X, cy, ridge_height)
ridge_end = (max_pt.X, cy, ridge_height)
guid = rs.AddLine(ridge_start, ridge_end)
print(json.dumps({{"guid": str(guid)}}))
'''
    })
    outer = json.loads(result['content'][0]['text'])
    stdout = outer.get('stdout', '{}')
    inner = json.loads(stdout)
    ridge_guid = inner.get('guid')
    print(f'Ridge: {ridge_guid}')
    
    # Test loft
    result = await adapter.call_tool('run_python', {
        'script': f'''
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc

boundary = rs.coercecurve("{rect_guid}")
ridge = rs.coercecurve("{ridge_guid}")

if boundary and ridge:
    loft = rg.Brep.CreateFromLoft([boundary.ToNurbsCurve(), ridge.ToNurbsCurve()], rg.Point3d.Unset, rg.Point3d.Unset, rg.LoftType.Normal, False)
    if loft:
        guids = [sc.doc.Objects.AddBrep(b) for b in loft]
        sc.doc.Views.Redraw()
        print(json.dumps({{"guids": [str(g) for g in guids]}}))
    else:
        print(json.dumps({{"guids": []}}))
else:
    print(json.dumps({{"guids": []}}))
'''
    })
    outer = json.loads(result['content'][0]['text'])
    stdout = outer.get('stdout', '{}')
    inner = json.loads(stdout)
    print(f'Loft result: {inner}')

    await adapter.close()

asyncio.run(test_live())