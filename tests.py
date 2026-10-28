import unittest
from playlist_engine import HashTable, SongLinkedList, MaxHeap, BTree, binary_search

class DSATests(unittest.TestCase):
    def test_hash_table(self):
        h = HashTable(5)
        h.put("calm", {"title": "A"})
        h.put("calm", {"title": "B"})
        self.assertEqual(len(h.get("calm")), 2)

    def test_linked_list(self):
        ll = SongLinkedList()
        ll.append({"title": "One"})
        ll.append({"title": "Two"})
        self.assertEqual([x["title"] for x in ll.to_list()], ["One", "Two"])

    def test_heap(self):
        heap = MaxHeap()
        heap.push((2, "low"))
        heap.push((8, "high"))
        self.assertEqual(heap.pop()[1], "high")

    def test_btree(self):
        tree = BTree()
        for i in range(1, 20):
            tree.insert(i, {"id": i})
        self.assertEqual(tree.search(13)["id"], 13)
        self.assertIsNone(tree.search(100))

    def test_binary_search(self):
        songs = [{"id": i} for i in range(1, 10)]
        self.assertEqual(binary_search(songs, 7)["id"], 7)
        self.assertIsNone(binary_search(songs, 20))

if __name__ == "__main__":
    unittest.main()
