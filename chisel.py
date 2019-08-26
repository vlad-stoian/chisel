import argparse
import os

import utils

parser = argparse.ArgumentParser()
parser.add_argument("--product-path", help="path to your .pivotal file")

args = parser.parse_args()
print(args)

product_size = os.path.getsize(args.product_path)

utils.parse_product(args.product_path)
