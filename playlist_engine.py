import csv
import os
import re
import time
from collections import defaultdict, deque
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LogisticRegression

class HashTable:
    """Separate chaining hash table: category -> list of songs."""
    def __init__(self, size=31):
        self.size = size
        self.buckets = [[] for _ in range(size)]

    def _index(self, key):
        return sum(ord(ch) for ch in str(key).lower()) % self.size

    def put(self, key, value):
        bucket = self.buckets[self._index(key)]
        for existing_key, values in bucket:
            if existing_key == key:
                values.append(value)
                return
        bucket.append((key, [value]))

    def get(self, key):
        for existing_key, values in self.buckets[self._index(key)]:
            if existing_key == key:
                return list(values)
        return []

class SongNode:
    def __init__(self, song):
        self.song = song
        self.next = None

class SongLinkedList:
    """Singly linked list used to store the final playlist."""
    def __init__(self):
        self.head = None
        self.tail = None
        self.length = 0

    def append(self, song):
        node = SongNode(song)
        if not self.head:
            self.head = self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self.length += 1

    def to_list(self):
        result, current = [], self.head
        while current:
            result.append(current.song)
            current = current.next
        return result

class MaxHeap:
    """Heap-based priority queue; highest score is removed first."""
    def __init__(self):
        self.data = []

    def push(self, item):
        self.data.append(item)
        i = len(self.data) - 1
        while i > 0:
            parent = (i - 1) // 2
            if self.data[parent][0] >= self.data[i][0]:
                break
            self.data[parent], self.data[i] = self.data[i], self.data[parent]
            i = parent

    def pop(self):
        if not self.data:
            return None
        self.data[0], self.data[-1] = self.data[-1], self.data[0]
        item = self.data.pop()
        i = 0
        while True:
            left, right = 2*i + 1, 2*i + 2
            largest = i
            if left < len(self.data) and self.data[left][0] > self.data[largest][0]:
                largest = left
            if right < len(self.data) and self.data[right][0] > self.data[largest][0]:
                largest = right
            if largest == i:
                break
            self.data[i], self.data[largest] = self.data[largest], self.data[i]
            i = largest
        return item

class BTreeNode:
    def __init__(self, leaf=True):
        self.leaf = leaf
        self.keys = []
        self.children = []

class BTree:
    """Small B-tree implementation used to demonstrate indexed song-ID insertion/search."""
    def __init__(self, degree=2):
        self.t = degree
        self.root = BTreeNode()

    def search(self, key, node=None):
        node = node or self.root
        i = 0
        while i < len(node.keys) and key > node.keys[i][0]:
            i += 1
        if i < len(node.keys) and key == node.keys[i][0]:
            return node.keys[i][1]
        if node.leaf:
            return None
        return self.search(key, node.children[i])

    def insert(self, key, value):
        root = self.root
        if len(root.keys) == 2*self.t - 1:
            new_root = BTreeNode(leaf=False)
            new_root.children.append(root)
            self._split_child(new_root, 0)
            self.root = new_root
        self._insert_nonfull(self.root, (key, value))

    def _split_child(self, parent, index):
        t = self.t
        child = parent.children[index]
        sibling = BTreeNode(leaf=child.leaf)
        middle = child.keys[t-1]
        sibling.keys = child.keys[t:]
        child.keys = child.keys[:t-1]
        if not child.leaf:
            sibling.children = child.children[t:]
            child.children = child.children[:t]
        parent.children.insert(index+1, sibling)
        parent.keys.insert(index, middle)

    def _insert_nonfull(self, node, item):
        i = len(node.keys)-1
        if node.leaf:
            node.keys.append(item)
            while i >= 0 and item[0] < node.keys[i][0]:
                node.keys[i+1] = node.keys[i]
                i -= 1
            node.keys[i+1] = item
        else:
            while i >= 0 and item[0] < node.keys[i][0]:
                i -= 1
            i += 1
            if len(node.children[i].keys) == 2*self.t-1:
                self._split_child(node, i)
                if item[0] > node.keys[i][0]:
                    i += 1
            self._insert_nonfull(node.children[i], item)

def binary_search(sorted_songs, song_id):
    """Iterative binary search. Input must be sorted by numeric song ID."""
    low, high = 0, len(sorted_songs)-1
    while low <= high:
        mid = (low + high)//2
        current = int(sorted_songs[mid]["id"])
        if current == song_id:
            return sorted_songs[mid]
        if current < song_id:
            low = mid + 1
        else:
            high = mid - 1
    return None

def bubble_sort_by_score(songs):
    """Bubble sort, descending recommendation score; included for DSA demonstration."""
    items = list(songs)
    n = len(items)
    for i in range(n):
        swapped = False
        for j in range(0, n-i-1):
            if items[j]["score"] < items[j+1]["score"]:
                items[j], items[j+1] = items[j+1], items[j]
                swapped = True
        if not swapped:
            break
    return items

class PlaylistEngine:
    def __init__(self, csv_path):
        self.songs = []
        self.by_mood = HashTable()
        self.by_genre = HashTable()
        self.by_artist = HashTable()
        self.btree = BTree()
        self.graph = defaultdict(list)
        self.load_songs(csv_path)
        self.train_recommendation_model()

    def load_songs(self, path):
        with open(path, newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                row["id"] = int(row["id"])
                row["rating"] = float(row["rating"])
                row["energy"] = int(row["energy"])
                self.songs.append(row)
                self.by_mood.put(row["mood"].lower(), row)
                self.by_genre.put(row["genre"].lower(), row)
                self.by_artist.put(row["artist"].lower(), row)
                self.btree.insert(row["id"], row)
        self.songs.sort(key=lambda s: s["id"])
        # Similarity graph: connect songs that share mood or genre.
        for song in self.songs:
            for other in self.songs:
                if song["id"] != other["id"] and (
                    song["mood"] == other["mood"] or song["genre"] == other["genre"]
                ):
                    self.graph[song["id"]].append(other["id"])

    def train_recommendation_model(self):
        """Fit a TF-IDF text model on song metadata for content-based recommendations."""
        documents = []
        for song in self.songs:
            documents.append(" ".join([
                song.get("title", ""), song.get("artist", ""),
                song.get("genre", ""), song.get("mood", ""),
                song.get("language", ""), song.get("description", ""),
                song.get("title", "").replace("-", " ")
            ]))
        self.tfidf_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.song_vectors = self.tfidf_vectorizer.fit_transform(documents)
        # Supervised multi-class classifier: learn mood labels from song metadata.
        mood_labels = [song.get("mood", "calm").lower() for song in self.songs]
        self.mood_classifier = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
        self.mood_classifier.fit(self.song_vectors, mood_labels)
        self.ai_model_name = "Hybrid TF-IDF + Logistic Regression Recommender"

    def ai_similarity_scores(self, request_text):
        """Return cosine similarity between the user's prompt and every song profile."""
        query = (request_text or "").strip()
        if not query:
            return [0.0] * len(self.songs)
        query_vector = self.tfidf_vectorizer.transform([query])
        return cosine_similarity(query_vector, self.song_vectors).flatten().tolist()

    def predict_mood_probabilities(self, request_text):
        """Predict mood probabilities from the user's text using a trained classifier."""
        query = (request_text or "").strip()
        if not query:
            return {}
        vector = self.tfidf_vectorizer.transform([query])
        probabilities = self.mood_classifier.predict_proba(vector)[0]
        return {label: float(prob) for label, prob in zip(self.mood_classifier.classes_, probabilities)}

    def detect_preferences(self, request_text):
        """Simple keyword-based NLP baseline, not a trained AI model."""
        text = request_text.lower()
        mood_words = {
            "calm": ["calm", "peaceful", "relax", "study", "focus", "soft"],
            "happy": ["happy", "cheerful", "fun", "feel good"],
            "sad": ["sad", "emotional", "heartbreak", "lonely"],
            "romantic": ["romantic", "love", "date"],
            "energetic": ["energetic", "workout", "gym", "dance", "party", "hype"]
        }
        genre_words = {
            "Tamil": ["tamil", "kollywood"],
            "Pop": ["pop"],
            "Lo-fi": ["lo-fi", "lofi"],
            "Rock": ["rock"],
            "Classical": ["classical"],
            "Hip-Hop": ["hip-hop", "hip hop", "rap"]
        }
        mood, genre = "any", "any"
        for label, words in mood_words.items():
            if any(word in text for word in words):
                mood = label
                break
        for label, words in genre_words.items():
            if any(word in text for word in words):
                genre = label
                break
        return mood, genre

    def bfs(self, start_id, allowed_ids, limit=12):
        visited, order = set(), []
        queue = deque([start_id])
        while queue and len(order) < limit:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if current in allowed_ids:
                order.append(current)
            for neighbour in self.graph.get(current, []):
                if neighbour not in visited:
                    queue.append(neighbour)
        return order

    def dfs(self, start_id, allowed_ids, limit=12):
        visited, order, stack = set(), [], [start_id]
        while stack and len(order) < limit:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            if current in allowed_ids:
                order.append(current)
            for neighbour in reversed(self.graph.get(current, [])):
                if neighbour not in visited:
                    stack.append(neighbour)
        return order

    def generate(self, request_text="", mood="any", genre="any", limit=8):
        detected_mood, detected_genre = self.detect_preferences(request_text)
        if mood == "any":
            mood = detected_mood
        if genre == "any":
            genre = detected_genre
        ai_scores = self.ai_similarity_scores(" ".join([request_text or "", mood if mood != "any" else "", genre if genre != "any" else ""]))
        ai_score_by_id = {song["id"]: ai_scores[index] for index, song in enumerate(self.songs)}
        mood_probabilities = self.predict_mood_probabilities(request_text)
        candidates = [dict(song) for song in self.songs]
        if mood != "any":
            candidates = [s for s in candidates if s["mood"].lower() == mood.lower()]
        if genre != "any":
            candidates = [s for s in candidates if s["genre"].lower() == genre.lower()]
        if not candidates:
            ai_scores = self.ai_similarity_scores(" ".join([request_text or "", mood if mood != "any" else "", genre if genre != "any" else ""]))
        ai_score_by_id = {song["id"]: ai_scores[index] for index, song in enumerate(self.songs)}
        candidates = [dict(song) for song in self.songs]
        max_rating = max((song["rating"] for song in candidates), default=5.0) or 5.0
        for song in candidates:
            ai_score = ai_score_by_id.get(song["id"], 0.0)
            predicted_mood_score = mood_probabilities.get(song["mood"].lower(), 0.0)
            genre_match = 1.0 if genre != "any" and song["genre"].lower() == genre.lower() else 0.0
            explicit_mood_match = 1.0 if mood != "any" and song["mood"].lower() == mood.lower() else 0.0
            rating_score = song["rating"] / max_rating
            song["ai_match"] = round(ai_score * 100, 1)
            song["predicted_mood"] = max(mood_probabilities, key=mood_probabilities.get) if mood_probabilities else "unknown"
            # Hybrid score combines text similarity, classifier probability, user filters and rating.
            score = (ai_score * 50) + (predicted_mood_score * 25) + (genre_match * 15) + (explicit_mood_match * 15) + (rating_score * 10)
            song["score"] = round(score, 4)
        # Bubble sort demonstrates sorting; heap selects top-ranked songs.
        ranked = bubble_sort_by_score(candidates)
        heap = MaxHeap()
        for song in ranked:
            heap.push((song["score"], song))
        selected = []
        while len(selected) < max(1, min(limit, 30)):
            item = heap.pop()
            if item is None:
                break
            selected.append(item[1])
        # Linked list stores playlist order.
        linked = SongLinkedList()
        for song in selected:
            linked.append(song)
        playlist = linked.to_list()
        allowed = {s["id"] for s in candidates}
        if playlist:
            bfs_ids = self.bfs(playlist[0]["id"], allowed)
            dfs_ids = self.dfs(playlist[0]["id"], allowed)
        else:
            bfs_ids, dfs_ids = [], []
        return {
            "playlist": [{k: v for k, v in s.items() if k != "score"} for s in playlist],
            "detected": {"mood": mood, "genre": genre},
            "ai_model": {"name": self.ai_model_name, "type": "Hybrid NLP recommender: TF-IDF + cosine similarity + Logistic Regression mood classifier", "status": "trained_on_song_catalogue_at_startup", "classifier": "Multiclass Logistic Regression", "predicted_mood_probabilities": {key: round(value, 3) for key, value in mood_probabilities.items()}, "purpose": "Combines text similarity with a supervised mood prediction model, selected genre/mood preferences and song ratings."},
            "explanation": "The hybrid model vectorizes song metadata with TF-IDF, compares the prompt with song profiles using cosine similarity, and uses a Logistic Regression classifier trained on catalogue mood labels to estimate mood probabilities. These signals are blended with genre/mood preferences and ratings; DSA structures then rank and assemble the playlist.",
            "algorithm_demo": {
                "hash_table": "Used for mood, genre, and artist lookup (separate chaining).",
                "binary_search": "Song IDs are sorted; iterative binary search is available in the engine.",
                "binary_search_example": binary_search(self.songs, playlist[0]["id"])["title"] if playlist and binary_search(self.songs, playlist[0]["id"]) else None,
                "sorting": "Bubble sort ranks matching songs by recommendation score.",
                "heap": "Max-heap selects the highest-scoring songs first.",
                "b_tree": "B-Tree indexes songs by ID; example lookup returns the selected song.",
                "b_tree_example": self.btree.search(playlist[0]["id"])["title"] if playlist else None,
                "graph_bfs_ids": bfs_ids,
                "graph_dfs_ids": dfs_ids,
                "linked_list": f"Final playlist stored as a linked list with {len(playlist)} nodes."
            }
        }

    def stats(self):
        return {
            "songs": len(self.songs),
            "moods": sorted({s["mood"] for s in self.songs}),
            "genres": sorted({s["genre"] for s in self.songs}),
            "artists": len({s["artist"] for s in self.songs})
        }
