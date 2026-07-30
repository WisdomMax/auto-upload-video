import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import catalog_builder
catalog_builder.build_catalog()
print("Catalog rebuild finished successfully!")
