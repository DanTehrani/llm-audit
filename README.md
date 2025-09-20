# LLM Audit

# Setup

### 1. Install dependencies
```bash
uv sync
```

### 2. Create .env file
```bash
cp .env.example .env
```

### 3. Add your OpenAI API key to the .env file

```bash
OPENAI_API_KEY=your_api_key
```

# Run

### Run audit for a sample contract

```bash
python main.py
```