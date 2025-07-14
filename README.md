# Certification Assistant

## Getting Started

### 1. Obtain a Gemini (Google) API Key

- Go to [Google AI Studio](https://aistudio.google.com/) and sign in with your Google account.
- Create a new API key.
- Copy the API key.

### 2. Configure the API Key

- Open the `docker-compose.yml` file.
- Find the `GOOGLE_API_KEY` environment variable under the `web` service.
- Replace its value with your new Gemini API key:
  ```yaml
  - GOOGLE_API_KEY=your-gemini-api-key-here
  ```
- (Optional) You can also use OpenAI by setting the `OPENAI_API_KEY` variable, but note that OpenAI is not free.

### 3. Run the Project

- In your terminal, run:
  ```sh
  docker compose up --build
  ```
- Once the containers are running, open your browser and go to:
  [http://localhost:8501/](http://localhost:8501/)

## Notes
- You can select between Gemini (Google) and OpenAI as the LLM provider in the sidebar of the web app.
- For best results and free usage, use Gemini with your Google API key.
- For more information on Gemini API keys, visit [Google AI Studio](https://aistudio.google.com/).