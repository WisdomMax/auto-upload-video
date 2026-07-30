import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

def get_details():
    pending_ids = [84, 85]
    for pid in pending_ids:
        item = database.get_item(pid)
        if item:
            print(f"--- ID: {pid} ---")
            for k, v in item.items():
                print(f"{k}: {v}")
            print()

if __name__ == "__main__":
    get_details()
