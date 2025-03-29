# MST Test Suite

Test suite for [atproto-flavour](https://atproto.com/specs/repository) merkle search tree ops.

Note: this is very WIP, test format may change based on feedback.

At time of writing, I've only validated test cases against my own implementation. They may be wrong!

This test suite is not authoritative but it intends to strictly conform to the atproto specification.

## Test Case Visualiser

To aid debugging, I wrote a tool to visualise test cases.

Run `python3 scripts/render_testcase_html.py path_to_testcase.json` and an HTML document will be generated and rendered in your browser. Like so:

![image](https://github.com/user-attachments/assets/db6eeab3-2784-4b55-a346-0787ad03d1cc)

TODO: document dependencies and how to install them

## Using the Tests

Test cases are stored as JSON files in the `./tests/` directory. They're organised into subdirectories, but you shouldn't expect any particular layout. It's recommended that you find the tests by recursively scanning the directory for all `.json` files.

There are multiple test types, each with their own format. They're identified by a `$type` field.

The format of each test type is specified below. (Currently only a `mst-diff` type is specified, but more are planned.)

### `mst-diff` test case format

```json
{
	"$type": "mst-diff",
	"description": "a description of what this tests for",
	"inputs": {
		"mst_a": "./path/to/a.car",
		"mst_b": "./path/to/b.car"
	},
	"results": {
		"created_nodes": ["b32cid", "..."],
		"deleted_nodes": ["b32cid", "..."],
		"record_ops": [
			{
				"rpath": "blah",
				"old_value": "b32cid or null",
				"new_value": "b32cid or null",
			}, "..."
		],
		"proof_nodes": ["b32cid", "..."],
		"inductive_proof_nodes": ["b32cid", "..."],
		"firehose_cids": ["b32cid", "..."]
	}
}
```

CAR paths are relative to the root of this git repo. Note: the CARs here only store MST blocks, no record values are stored (they're not relevant to the tests).

`created_nodes`, `deleted_nodes`, `proof_nodes`, `inductive_proof_nodes`, and `firehose_cids` are lists of base32-encoded CIDs. Logically they are sets, and the order of the elements does not matter for correctness, but for consistency they are stored in string-sorted order.

`record_ops` is also logically a set, but is similarly stored in rpath-sorted order. "created" records have `old_value=null`, "deleted" records have `new_value=null`, and "updated" records have non-null values for both.

`proof_nodes` is the CIDs of the MST nodes required for:

1. inclusion proofs for all newly created or updated records

2. exclusion proofs for all newly deleted records

This is *often* identical to the `created_nodes` list, but sometimes a superset, and sometimes a subset!

`inductive_proof_nodes` should be the set of CIDs of the MST nodes required for ["MST Operation Inversion"](https://github.com/bluesky-social/proposals/tree/main/0006-sync-iteration#commit-validation-mst-operation-inversion). The inductive proof should be verified by applying the ops in reverse order.

`firehose_cids` is the set of CIDs you'd expect to broadcast on the "firehose" in the `blocks` CAR (minus the commit object). That is, the union of `created_nodes`, `new_value`s from `record_ops`, and `proof_nodes`. In these test cases I aim to encode the *minimal* set of blocks, but it is legal to include superfluous blocks (within reason).

TODO: is `firehose_cids` pointless?

It should also be possible to run these tests "backwards", applying the ops list to `mst_a` and checking whether you end up at `mst_b` (optionally verifying inclusion/exclusion proofs as you go).

## About The "Exhaustive" Tests

You can use the test cases without having read/understood this section, but it might be informative if you're trying to understand why your tests aren't passing, or if you want to know what's actually being tested and why.

There are infinitely many possible valid MST states (so we can never do truly exhaustive testing), but I think *most* of the interesting trees (for diffing purposes) can be enumerated as "subset-trees" of the following base tree:

```
                                    |
                            (. "k/39", h=2 .)
                   _________/               \_________
                  /                                   \
         (. "k/02", h=1 .)                     (. "k/48", h=1 .)
         /               \                     /               \
(. "k/00", h=0 .) (. "k/04", h=0 .)   (. "k/40", h=0 .) (. "k/49", h=0 .)

```

The rpaths here (`k/*`) were "mined" to be at the required heights (denoted by `h`) to produce this particular MST shape (i.e. a "perfect" binary tree).

There are 7 nodes in the full tree, each containing one rpath and two child nodes (except for the leaf nodes, with no children).

By "subset-trees" I mean the above tree with some subset of the rpaths having been deleted.

There are $2^7$ (128) possible subset-trees (including the empty tree, and the orginal tree).

If we were to diff every possible pair of these trees, that gives us 16384 test cases - a lot, but still practical to test them all!

Note that this set of test cases currently only tests record creation and deletion, not updates.

# CAR Canonicalization

A "canonical" CAR file is one where the blocks are stored in CID-sorted order, with no duplicates or extras. (NOTE: CIDs are sorted on their byte representation! This is different to the sort of their base32 string representation!)

atproto itself doesn't (currently) care about the order of blocks within a CAR, but sorting makes the test cases deterministic and easier to compare against. For validating your own test results (when a CAR is part of the reference result), it's up to you whether you parse the CAR and compare it logically, or serialise a canonical CAR and compare against the reference CAR bytes.

For these tests, the "root" of the CAR is the MST root, and there is no commit object.
