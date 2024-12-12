from typing import List

import json
import tempfile
import time

from atmst.mst.node_store import NodeStore
from atmst.blockstore.car_file import ReadOnlyCARBlockStore
from cbrrr import CID

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
		self.dot.node("root", "root", width="0", height="0")
		self.dot.edge("root", self.root.encode())
		self.graph_node(self.root)
		return self.dot

	def edge(self, src: CID, dst: CID):
		self.dot.edge(f"{src.encode()}:{dst.encode()}:s", f"{dst.encode()}:n", tooltip=dst.encode())

	def graph_node(self, node_cid: CID):
		node = self.ns.get_node(node_cid)
		members = []
		sub = node.subtrees[0]
		DOT = "●"
		if sub is not None:
			members.append(f"<{sub.encode()}> {DOT}")
			self.edge(node_cid, sub)
			self.graph_node(sub)
		else:
			members.append(DOT)
		for sub, k in zip(node.subtrees[1:], node.keys):
			members.append(f"\"{k}\"")
			if sub is not None:
				members.append(f"<{sub.encode()}> {DOT}")
				self.edge(node_cid, sub)
				self.graph_node(sub)
			else:
				members.append(DOT)
		color = self.plte.get(node_cid)
		if color is None:
			color = PALETTE[len(self.plte)]
			self.plte[node_cid] = color
		self.dot.node(node_cid.encode(), " | ".join(members), width="0", height="0", style="filled", fillcolor=color) # min-width, they'll grow to fit

def car_to_svg(car_path: str, plte={}) -> str:
	with open(car_path, "rb") as carfile:
		bs = ReadOnlyCARBlockStore(carfile)
		ns = NodeStore(bs)
		dot = TreeGrapher(ns, bs.car_root, plte).graph()
	graph = pydot.graph_from_dot_data(str(dot))[0] # yeah we import all of pydot just for this lol
	svg = graph.create_svg().decode()
	dtd, tag, body = svg.partition("<svg") # strip xml dtd
	return tag + body

def make_cid_ul(data: List[str], plte: dict) -> str:
	return f"<ul>{"".join(f'<li style="background-color: {plte[CID.decode(x)]}; padding: 0.5em 1em; width: fit-content">{x}</li>' for x in data)}</ul>"

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
		svg_a = car_to_svg(car_a, plte)
		svg_b = car_to_svg(car_b, plte)

		#svg_uri = "data:image/svg+xml;base64," + base64.b64encode(svg).decode()
		html.write(f"""
		<h1>Test case: {testcase_path}</h1>
		<p>protip: hover over graph nodes for their CIDs</p>
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
		<h2>Created Nodes:</h2>
		{make_cid_ul(testcase["results"]["created_nodes"], plte)}
		<h2>Deleted Nodes:</h2>
		{make_cid_ul(testcase["results"]["deleted_nodes"], plte)}
		<h2>Ops:</h2>
		<ul>{"".join(f"<li>{"update" if (op["old_value"] and op["new_value"]) else ("create" if op["new_value"] else "delete")} {op["rpath"]!r}</li>" for op in testcase["results"]["record_ops"])}</ul>
	</body>
</html>
	""")
	

if __name__ == "__main__":
	import sys
	if len(sys.argv) != 2:
		print(f"USAGE: {sys.argv[0]} path_to_testcase.json")
		exit()
	with tempfile.NamedTemporaryFile(suffix="_testcase.html") as tf:
		render_testcase(sys.argv[1], tf.name)
		webbrowser.open(tf.name)
		time.sleep(1) # race condition: give the browser time to open the fie...
