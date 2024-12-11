from typing import BinaryIO
from atmst.mst.node import MSTNode
from atmst.mst.node_store import NodeStore
from atmst.mst.node_wrangler import NodeWrangler
from atmst.mst.node_walker import NodeWalker
from atmst.blockstore import MemoryBlockStore
from atmst.blockstore.car_file import encode_varint
import cbrrr
from cbrrr import CID

class CarWriter:
	def __init__(self, stream: BinaryIO, root: cbrrr.CID) -> None:
		self.stream = stream
		header_bytes = cbrrr.encode_dag_cbor(
			{"version": 1, "roots": [root]}
		)
		stream.write(encode_varint(len(header_bytes)))
		stream.write(header_bytes)

	def write_block(self, cid: cbrrr.CID, value: bytes):
		cid_bytes = bytes(cid)
		self.stream.write(encode_varint(len(cid_bytes) + len(value)))
		self.stream.write(cid_bytes)
		self.stream.write(value)

keys = []
key_heights = [0, 1, 0, 2, 0, 1, 0] # if all these keys are added to a MST, it'll form a perfect binary tree.
i = 0
for height in key_heights:
	while True:
		key = f"k{i:02d}"
		i += 1
		if MSTNode.key_height(key) == height:
			keys.append(key)
			break

vals = [CID.cidv1_dag_cbor_sha256_32_from(cbrrr.encode_dag_cbor({"$type": "mst-test-data", "value_for": k})) for k in keys]

print(keys)
print(vals)

# we can reuse these
bs = MemoryBlockStore()
ns = NodeStore(bs)
wrangler = NodeWrangler(ns)

for i in range(2**len(keys)):
	filename = f"./cars/exhaustive/exhaustive_{i:03d}.car"
	root = ns.get_node(None).cid
	for j in range(len(keys)):
		if (i>>j) & 1:
			#filename += f"_{keys[j]}h{key_heights[j]}"
			root = wrangler.put_record(root, keys[j], vals[j])
	#filename += ".car"
	print(i, filename)

	car_blocks = []
	for node in NodeWalker(ns, root).iter_nodes():
		car_blocks.append((node.cid, node.serialised))

	assert(len(set(cid for cid, val in car_blocks)) == len(car_blocks)) # no dupes

	with open(filename, "wb") as carfile:
		car = CarWriter(carfile, root)
		for cid, val in sorted(car_blocks, key=lambda x: bytes(x[0])):
			car.write_block(cid, val)
