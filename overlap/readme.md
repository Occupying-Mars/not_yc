# Overlap

## Description

Overlap is a project designed to manage and searching podcast clips through transcript collections using Qdrant, a vector search engine. It leverages OpenAI's API to generate embeddings for text data and stores these embeddings in Qdrant for efficient similarity search.

## Setup

### Prerequisites

- Docker
- Python 3.x
- pip

### Setting Up Qdrant

1. **Pull the Qdrant Docker Image:**

   ```sh
   docker pull qdrant/qdrant
   ```
2. **Run Qdrant:**

   ```sh
   docker run -p 6333:6333 -p 6334:6334 \
       -v $(pwd)/qdrant_storage:/qdrant/storage:z \
       qdrant/qdrant
   ```

### Setting Up the Project

1. **Clone the Repository:**

   ```sh
   git clone <repository_url>
   cd overlap
   ```
2. **Create and Activate a Virtual Environment:**

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. **Install Dependencies:**

   ```sh
   pip install -r requirements.txt
   ```
4. **Set Up the `.env` File:**
   Create a `.env` file in the root directory of the project and add your OpenAI API key:

   ```env
   OPENAI_API_KEY = <your-api-key-here>
   ```

### Running the Project

1. **Start the Qdrant Docker Container:**
   Ensure Qdrant is running as described in the "Setting Up Qdrant" section.
2. **Run the Streamlit app:**

   ```sh
   streamlit run app.py
   ```
