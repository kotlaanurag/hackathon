from openai import AzureOpenAI
from configs import Config


def get_llm_client() -> AzureOpenAI:
    """Create and return an Azure OpenAI client."""
    return AzureOpenAI(
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        api_key=Config.AZURE_OPENAI_API_KEY,
        api_version=Config.AZURE_OPENAI_API_VERSION,
    )


def get_chat_response(client: AzureOpenAI, messages: list) -> str:
    """Get a response from the Azure OpenAI model using the Responses API."""
    # Build input for Responses API from messages list
    input_messages = []
    for msg in messages:
        if msg["role"] == "system":
            input_messages.append({"role": "developer", "content": msg["content"]})
        else:
            input_messages.append({"role": msg["role"], "content": msg["content"]})

    response = client.responses.create(
        model=Config.AZURE_OPENAI_DEPLOYMENT,
        input=input_messages,
    )
    return response.output_text
