# plaitime

This is a really simple & lean program to chat with a local LLM powered by the excellent ollama library. It has a rewind feature that allows you to explore alternative paths.

**PRs with improvements (optical, technical, ...) are very welcome.**

I made this to experiment with different models and prompts, use cases includes:

- Chat with a generic AI assistant just like in ChatGPT
- Let LLM impersonate characters to chat with
- Set up the LLM for pen-and-paper roleplay

## Installation

```
pip install plaitime
```

You need to pull the models with ollama, for example:

```
ollama pull llama3.2
```

See the excellent ollama online documentation what models are available.

## Usage

You can create "characters" that use different models and prompts. Each character has their own message history, which is persisted unless you turn that off. Use the combo-box to switch characters.

### Chatting

Pressing Enter sends the text to the LLM. When you do that the first time, the LLM may need some time to ramp up, be patient. In the following it will react faster.

You can interrupt the generation or rewind the chat by pressing Escape. This gives you the opportunity to change your previous message, ie. to prevent the LLM from moving into an undesired direction. Another way to correct the LLM is to change the system prompt of the model. The model will always see the current system prompt for its next generation, so you can change its factual memory or personality in the middle of the conversation.

### Changing model or system prompt

To create a new character, use the "New character" button. To change the model or system prompt of an existing character, use the "Configure" button. The system prompt is special, because it guides the overall behavior of the LLM. Use it to make the LLM adhere to a given response format, to configure its personality, to provide permanent facts. In short, the system prompt can be regarded as static memory for the LLM.

The LLM will never forget its system prompt, because the program is aware of the size of the context window for each model and will clip the conversation so that it fits into the context window without losing the system prompt. This is important because otherwise your model will forget how to behave.

For some LLMs you can set the temperature, which makes the model more creative, while a low temperature makes it more predictable.

### Limitations and workarounds

Because of the finite message window, the LLM will eventually forget details of what you were talking about earlier and become inconsistent. A workaround is to let the LLM periodically make a story summary, which you usually need to edit to fill in details that the LLM missed. You can do that with the "summary" button (which may take a while to complete).

## Contributing

See the issues on Github and feel free to contribute!

Note, however, that I want to keep plaitime simple and hackable.
