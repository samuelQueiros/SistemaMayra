"""Provedores de IA aceitos pelo sistema (Configurações → Inteligência
Artificial). Fonte única: o backend valida por aqui e a tela lista a partir
de GET /api/settings/ai/provedores.

Claude, GPT e Gemini têm conector próprio no LangChain. Os demais expõem uma
API compatível com a da OpenAI e entram pelo `ChatOpenAI` com outro
`base_url` — sem bibliotecas novas.

`leitura_pdf` diz como os PDFs de formulários (Relatório Por IA) chegam ao
modelo — importa porque no PDF do Google Forms a opção marcada é um desenho:
- "nativa": o PDF vai inteiro (o modelo lê texto e imagem);
- "imagens": cada página vai como imagem + o texto extraído (modelos que
  enxergam imagem mas não aceitam PDF);
- "texto": só o texto extraído (modelos sem visão — a opção marcada pode se
  perder; a tela avisa)."""

from dataclasses import dataclass, field
from typing import Literal

LeituraPdf = Literal["nativa", "imagens", "texto"]


@dataclass(frozen=True)
class Provedor:
    """Provedor de IA aceito: id, nome, como lê PDF (`leitura_pdf`: inteiro, páginas como imagem ou só texto),
    modelos sugeridos, link para obter a chave e, nos compatíveis com a OpenAI, o endereço base."""

    id: str
    nome: str
    leitura_pdf: LeituraPdf
    modelos: list[str] = field(default_factory=list)
    link_chave: str = ""
    # Só para provedores compatíveis com a API da OpenAI.
    base_url: str | None = None
    observacao: str | None = None


PROVEDORES: dict[str, Provedor] = {
    p.id: p
    for p in [
        Provedor(
            "anthropic",
            "Anthropic (Claude)",
            "nativa",
            ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"],
            "https://console.anthropic.com/settings/keys",
        ),
        Provedor(
            "openai",
            "OpenAI (ChatGPT / GPT)",
            "nativa",
            ["gpt-5", "gpt-5-mini"],
            "https://platform.openai.com/api-keys",
        ),
        Provedor(
            "google",
            "Google (Gemini)",
            "nativa",
            ["gemini-3.6-flash", "gemini-2.5-pro"],
            "https://aistudio.google.com/app/apikey",
            observacao=(
                "A assinatura do app do Gemini (Gemini Advanced / Google AI Pro) é separada da chave de API "
                "de desenvolvedor — a chave usa a cobrança do Google Cloud."
            ),
        ),
        Provedor(
            "openrouter",
            "OpenRouter (vários modelos com uma chave só)",
            "nativa",
            [
                "anthropic/claude-sonnet-4.5",
                "openai/gpt-5",
                "google/gemini-2.5-pro",
                "x-ai/grok-4",
                "meta-llama/llama-4-maverick",
                "deepseek/deepseek-chat",
                "mistralai/mistral-large",
                "qwen/qwen3-max",
            ],
            "https://openrouter.ai/keys",
            base_url="https://openrouter.ai/api/v1",
            observacao="Com uma chave do OpenRouter dá para usar modelos de quase todas as empresas. Escreva o modelo como empresa/modelo.",
        ),
        Provedor(
            "xai",
            "xAI (Grok)",
            "imagens",
            ["grok-4", "grok-4-fast"],
            "https://console.x.ai",
            base_url="https://api.x.ai/v1",
        ),
        Provedor(
            "mistral",
            "Mistral AI (Le Chat)",
            "imagens",
            ["mistral-large-latest", "mistral-medium-latest", "pixtral-large-latest"],
            "https://console.mistral.ai/api-keys",
            base_url="https://api.mistral.ai/v1",
        ),
        Provedor(
            "groq",
            "Meta Llama (via Groq)",
            "imagens",
            [
                "meta-llama/llama-4-maverick-17b-128e-instruct",
                "meta-llama/llama-4-scout-17b-16e-instruct",
                "llama-3.3-70b-versatile",
            ],
            "https://console.groq.com/keys",
            base_url="https://api.groq.com/openai/v1",
        ),
        Provedor(
            "qwen",
            "Alibaba (Qwen)",
            "imagens",
            ["qwen-max", "qwen-vl-max", "qwen-plus"],
            "https://bailian.console.alibabacloud.com/?apiKey=1",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        ),
        Provedor(
            "deepseek",
            "DeepSeek",
            "texto",
            ["deepseek-chat", "deepseek-reasoner"],
            "https://platform.deepseek.com/api_keys",
            base_url="https://api.deepseek.com",
            observacao="O DeepSeek não lê imagens: no Relatório Por IA ele recebe só o texto dos PDFs e pode não identificar a opção marcada no Google Forms.",
        ),
        Provedor(
            "cohere",
            "Cohere (Command)",
            "texto",
            ["command-a-03-2025", "command-r-plus"],
            "https://dashboard.cohere.com/api-keys",
            base_url="https://api.cohere.ai/compatibility/v1",
            observacao="O Cohere Command não lê imagens: no Relatório Por IA ele recebe só o texto dos PDFs e pode não identificar a opção marcada no Google Forms.",
        ),
    ]
}


def provedor(id_: str) -> Provedor | None:
    """Dados do provedor pelo id, ou None se não existir."""
    return PROVEDORES.get(id_)
