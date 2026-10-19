from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory


def load_database(path=None):
    if path is None:
        path = Path(get_package_share_directory('warehouse_database')) / 'config' / 'box_database.yaml'
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    data['boxes'] = {int(k): v for k, v in data.get('boxes', {}).items()}
    return data
