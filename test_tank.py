from services.asset_service import AssetService

s = AssetService()
status = s.get_tank_status_by_building('BLD_001', mode='latest')
print(f"Tank Status: {status}")
print(f"Tank %: {status.get('level_percentage')}")
