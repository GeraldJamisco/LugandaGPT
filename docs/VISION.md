# Vision

## Mission

LugandaGPT is a research and engineering project to build a
**Luganda-native conversational language model**: a system that understands
and generates natural Luganda and can hold useful, context-aware
conversations in the language.

## What this is not

LugandaGPT is **not**:

- merely a translation application;
- a Luganda education website;
- a thin wrapper around another provider's chatbot API.

The goal is a model with genuine command of Luganda, not a translation
shim placed over a general-purpose model.

## Long-term goal

An AI system that can:

- understand and generate natural Luganda;
- communicate in formal and educated Luganda;
- handle everyday and colloquial Luganda;
- handle Luganda-English code-switching;
- follow instructions;
- maintain conversational context;
- explain concepts and answer questions;
- perform useful reasoning;
- reflect Ugandan linguistic and cultural context accurately.

## Initial scope

- **Text-only.** Audio, speech, and multimodal work are out of scope for now.
- Focus on Luganda, with Luganda-English code-switching as a required
  capability.

## Target language varieties

LugandaGPT should handle a range of registers and varieties, including:

- **Formal / educated Luganda**, as used in writing, education, and
  formal settings.
- **Everyday Luganda**, meaning ordinary conversational usage.
- **Colloquial Luganda**, covering informal speech, slang, and regional
  variation.
- **Luganda-English code-switching**, the common mixing of Luganda and
  English in everyday Ugandan communication.

## Intended capabilities

Instruction following, multi-turn conversation, explanation, reasoning,
register adaptation, and cultural/linguistic interpretation.

## Non-goals

- Translation as the primary product.
- Photo/textbook-style language-teaching content.
- Speech, image, or multimodal capabilities (initial phase).
- Deployment or public release before evaluation and approval.

## Current status

**No trained LugandaGPT model currently exists.** The repository currently
contains project documentation and, as the project develops, tooling for
data handling, tokenizer evaluation, and evaluation. Nothing here should be
interpreted as a claim that a model has been built, trained, or evaluated.

Implementation strategy, base model, architecture, tokenizer, parameter
count, training method, and compute provider remain **undecided** until
sufficient research and benchmarking are completed. See
`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/DECISIONS.md`.
