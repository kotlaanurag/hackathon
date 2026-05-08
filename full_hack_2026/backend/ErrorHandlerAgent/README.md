# Error Handler Bot

A Teams-style chatbot that analyzes PCS field mapping errors, explains them using a reference mapping file, and guides users through resolution — powered by Azure OpenAI.

## Setup

1. **Install dependencies**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure `.env`**
   ```
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your-key
   AZURE_OPENAI_DEPLOYMENT=your-deployment-name
   AZURE_OPENAI_API_VERSION=2025-04-01-preview
   ```

3. **Run**
   ```bash
   streamlit run app.py
   ```

## Docker

```bash
docker-compose up --build
```

## Output

After the conversation, a JSON file is saved to `output/`:

```json
{
  "sessionid": "a1c4e8d2",
  "userid": "Sarah Mitchell",
  "error_details": "...",
  "action": "..."
}
```
