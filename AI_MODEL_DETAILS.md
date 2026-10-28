# VibeTune Advanced AI Model

## Model architecture
VibeTune uses a hybrid content-based NLP recommender made from:

1. **TF-IDF (word and bigram features):** converts each song's title, artist, genre, mood, language and description into numeric vectors.
2. **Cosine similarity:** measures similarity between the user's text prompt and each song profile.
3. **Multiclass Logistic Regression:** trained at application startup on the included song catalogue, using the song metadata vectors and mood labels. It estimates probabilities for the catalogue's mood classes.
4. **Hybrid ranking:** blends text similarity, predicted mood probability, explicit mood/genre matches and song rating.
5. **DSA selection:** existing Bubble Sort, Max Heap, Linked List, Hash Table, B-Tree, Binary Search and graph BFS/DFS remain in the project.

## Is it a real AI model?
Yes. Logistic Regression is a supervised machine-learning model. TF-IDF + cosine similarity is the content-retrieval component. The model is trained on the sample catalogue each time the backend starts. It is not a generative AI model or a deep neural network, and its quality depends on the size and quality of the supplied catalogue. The included dataset is small, so describe it as a prototype model in a presentation.

## Run
```cmd
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000.

Dependencies: Flask and scikit-learn.
