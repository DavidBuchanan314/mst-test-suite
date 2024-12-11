# MST Test Suite

Test suite for [atproto-flavour](https://atproto.com/specs/repository) merkle search tree ops.

Note: this is very WIP, test format may change based on feedback.

At time of writing, I've only validated test cases against my own implementation. They may be wrong!

## Diff test case format

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
		"firehose_cids": ["b32cid", "..."]
	}
}
```

CAR paths are relative to the root of this git repo.

`created_nodes`, `deleted_nodes`, and `firehose_cids` are lists of base32-encoded CIDs. Logically they are sets, and the order of the elements does not matter for correctness, but for consistency they are stored in string-sorted order.

`record_ops` is also logically a set, but is similarly stored in rpath-sorted order. "created" records have `old_value=null`, "deleted" records have `new_value=null`, and "updated" records have non-null values for both.

`firehose_cids` is the CIDs you'd expect to broadcast on "the firehose" in the `blocks` CAR. That is, the union of `created_nodes`, `new_value`s from `record_ops`, and any additional MST blocks you need for exclusion proofs of deleted records. In these test cases I aim to encode the *minimal* set of blocks, but it is legal to include superfluous blocks (within reason).

## About The Exhaustive Tests

You can use the test cases without having read/understood this section, but it might be informative if you're trying to understand why your tests aren't passing, or if you want to know what's actually being tested and why.

There are infinitely many possible valid MST states, but I think *most* of the interesting trees (for diffing purposes) can be enumerated as "subset-trees" of the following base tree:

```
                               |
                        (. "k30",h=2 .)
                 _______/             \_________
                /                               \
        (. "k11",h=1 .)                   (. "k34",h=1 .)
        /             \                   /             \
(. "k00",h=0 .) (. "k12",h=0 .)   (. "k32",h=0 .) (. "k35",h=0 .)

```

The rpaths here (`k*`) were "mined" to be at the required heights (denoted by `h`) to produce this particular MST shape (i.e. a "perfect" binary tree).

There are 7 nodes in the full tree, each containing one rpath and two child nodes (except for the leaf nodes, with no children).

By "subset-trees" I mean the above tree with some subset of the rpaths having been deleted.

There are $2^7$ (128) possible subset-trees (including the empty tree, and the orginal tree).

If we were to diff every possible pair of these trees, that gives us 16384 test cases - a lot, but still practical to test them all!


# CAR Canonicalization

A "canonical" CAR file is one where the blocks are stored in CID-sorted order. (NOTE: sorted on their byte representation! This is different to the sort of their string representation!). There should be no duplicate blocks, and no unnecessary blocks.

atproto itself doesn't (currently) care about the order of blocks within a CAR, but sorting makes the test cases deterministic and easier to compare against.

For these tests, the "root" of the CAR is the MST root, there is no commit object.
