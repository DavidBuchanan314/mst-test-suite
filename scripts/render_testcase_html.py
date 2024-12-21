from typing import List, Tuple

import json
import tempfile
import time

from atmst.mst.node_store import NodeStore
from atmst.blockstore import BlockStore, OverlayBlockStore
from atmst.blockstore.car_file import ReadOnlyCARBlockStore
from cbrrr import CID, decode_dag_cbor

import graphviz
import pydot
import webbrowser

# https://mokole.com/palette.html
PALETTE = [
	"#2f4f4f",
	"#2e8b57",
	"#800000",
	"#191970",
	"#808000",
	"#ff0000",
	"#ff8c00",
	"#ffd700",
	"#0000cd",
	"#ba55d3",
	"#00ff7f",
	"#adff2f",
	"#ff00ff",
	"#1e90ff",
	"#fa8072",
	"#dda0dd",
	"#87ceeb",
	"#ff1493",
	"#7fffd4",
	"#ffe4c4"
][::-1]

class TreeGrapher:
	def __init__(self, ns: NodeStore, root: CID, plte: dict):
		self.ns = ns
		self.root = root
		self.plte = plte

	def graph(self, title: str=None):
		self.dot = graphviz.Digraph(node_attr={"shape": "record"})
		if title is not None:
			self.dot.attr(label=title, labelloc="t")
		self.node("root", "root")
		self.dot.edge("root", self.root.encode())
		self.recurse_node(self.root)
		return self.dot

	def edge(self, src: CID, dst: CID):
		self.dot.edge(f"{src.encode()}:{dst.encode()}:s", f"{dst.encode()}:n", tooltip=dst.encode())

	def node(self, name: str, label: str, color=None):
		self.dot.node(name, label, fontname="Courier-Bold", fontsize="10pt", width="0", height="0", style="filled", fillcolor=color)

	def recurse_node(self, node_cid: CID):
		node = self.ns.get_node(node_cid)
		members = []
		sub = node.subtrees[0]
		DOT = "●"
		if sub is not None:
			members.append(f"<{sub.encode()}> {DOT}")
			self.edge(node_cid, sub)
			self.recurse_node(sub)
		else:
			members.append(DOT)
		for sub, k in zip(node.subtrees[1:], node.keys):
			members.append(f"\"{k}\"")
			if sub is not None:
				members.append(f"<{sub.encode()}> {DOT}")
				self.edge(node_cid, sub)
				self.recurse_node(sub)
			else:
				members.append(DOT)
		color = self.plte.get(node_cid)
		if color is None:
			color = PALETTE[len(self.plte)]
			self.plte[node_cid] = color
		self.node(node_cid.encode(), " | ".join(members), color=color) # min-width, they'll grow to fit

def car_to_svg(car_path: str, plte={}) -> Tuple[BlockStore, str]:
	#with open(car_path, "rb") as carfile:
	carfile = open(car_path, "rb")
	bs = ReadOnlyCARBlockStore(carfile)
	ns = NodeStore(bs)
	dot = TreeGrapher(ns, bs.car_root, plte).graph()
	graph = pydot.graph_from_dot_data(str(dot))[0] # yeah we import all of pydot just for this lol
	svg = graph.create_svg().decode()
	dtd, tag, body = svg.partition("<svg") # strip xml dtd
	return bs, tag + body

def make_cid_ul(ns: NodeStore, data: List[str], plte: dict) -> str:
	rows = []
	for cid_str in data:
		cid = CID.decode(cid_str)
		node = decode_dag_cbor(ns.get_node(cid).serialised)
		# convert cids to strings

		if node["l"]:
			node["l"] = node["l"].encode()
		for e in node["e"]:
			e["k"] = e["k"].decode()
			if e["t"]:
				e["t"] = e["t"].encode()
			if e["v"]:
				e["v"] = e["v"].encode()
		#print(node)
		node_json = json.dumps(node, indent=2)
		rows.append(f'''
			<li style="background-color: {plte[cid]}; padding: 0.5em 1em; width: fit-content">
			<details>
				<summary>{cid_str}</summary>
				<pre>{node_json}</pre>
			</details>
			</li>
		''')
	return f"<ul>{"".join(rows)}</ul>"

def render_testcase(testcase_path: str, out_path: str):
	with open(out_path, "w") as html:
		html.write("""\
<!DOCTYPE html>
<html>
	<head>
		<meta charset="utf8">
		<style>
			body {
				font-family: monospace;
			}
			table, th, td {
				border: 1px solid black;
				border-collapse: collapse;
			}
			td {
				padding: 1em;
				text-align: center;
			}
			th > h2 {
				margin: 0.5em 1em;
			}
			.cidlist > td {
				text-align: left;
				vertical-align: top;
			}
			th {
				text-align: left;
			}
			td > ul {
				padding-left: 0;
			}
			td li {
				list-style-type: none;
			}
		</style>
	</head>
	<body>
""")

		with open(testcase_path) as tf:
			testcase = json.load(tf)

		car_a = testcase["inputs"]["mst_a"]
		car_b = testcase["inputs"]["mst_b"]
		plte = {}
		bs_a, svg_a = car_to_svg(car_a, plte)
		bs_b, svg_b = car_to_svg(car_b, plte)
		bs = OverlayBlockStore(bs_a, bs_b)
		ns = NodeStore(bs)

		#svg_uri = "data:image/svg+xml;base64," + base64.b64encode(svg).decode()
		html.write(f"""
		<h1>Test case: {testcase_path}</h1>
		<p>hint: hover over graph nodes for their CIDs</p>
		<table>
			<tr>
				<th><h2>MST A: {car_a}</h2></th>
				<th><h2>MST B: {car_b}</h2></th>
			</tr>
			<tr>
				<td>{svg_a}</td>
				<td>{svg_b}</td>
			</tr>
		</table>
		<br/>
		<h1>Expected diff results:</h1>
		<p>hint: click a CID to expand</p>
		<table>
			<tr>
				<th><h2>Deleted Nodes:</h2></th>
				<th><h2>Created Nodes:</h2></th>
			</tr>
			<tr class="cidlist">
				<td>{make_cid_ul(ns, testcase["results"]["deleted_nodes"], plte)}</td>
				<td>{make_cid_ul(ns, testcase["results"]["created_nodes"], plte)}</td>
			</tr>
			<tr>
				<th></th>
				<th><h2>Proof Nodes:</h2></th>
			</tr>
			<tr class="cidlist">
				<td></td>
				<td>{make_cid_ul(ns, testcase["results"]["proof_nodes"], plte)}</td>
			</tr>
		</table>
		<h2>Ops:</h2>
		<ul>{"".join(f"<li>{"update" if (op["old_value"] and op["new_value"]) else ("create" if op["new_value"] else "delete")} {op["rpath"]!r}</li>" for op in testcase["results"]["record_ops"])}</ul>
	</body>
</html>
	""")
	

if __name__ == "__main__":
	import sys
	if len(sys.argv) not in [2, 3]:
		print(f"USAGE: {sys.argv[0]} path_to_testcase.json [output.html]")
		print("if no output is specified, a tmp file is created and opened in a browser")
		exit()
	if len(sys.argv) == 3:
		render_testcase(sys.argv[1], sys.argv[2])
	else:
		with tempfile.NamedTemporaryFile(suffix="_testcase.html") as tf:
			render_testcase(sys.argv[1], tf.name)
			webbrowser.open(tf.name)
			time.sleep(1) # race condition: give the browser time to open the fie...
