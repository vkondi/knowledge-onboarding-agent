# Deep Learning Fundamentals

Deep learning is a subfield of machine learning that uses neural networks with many layers to learn hierarchical representations of data.

## Neural Networks

A neural network is composed of layers of interconnected nodes (neurons). Each connection has a weight that is adjusted during training.

```
Input Layer → Hidden Layer(s) → Output Layer
   [x₁]          [h₁ h₂]           [ŷ]
   [x₂]     →    [h₃ h₄]    →
   [x₃]          [h₅ h₆]
```

### Activation Functions

Activation functions introduce non-linearity, enabling networks to model complex patterns.

| Function | Formula | Use case |
|---|---|---|
| ReLU | max(0, x) | Default for hidden layers — fast, avoids vanishing gradient |
| Sigmoid | 1 / (1 + e⁻ˣ) | Binary classification output |
| Softmax | eˣⁱ / Σeˣʲ | Multi-class output |
| Tanh | (eˣ - e⁻ˣ) / (eˣ + e⁻ˣ) | RNN hidden states |

### Forward Pass

Each neuron computes: `output = activation(weights · inputs + bias)`

### Backpropagation

The training algorithm. Uses the chain rule to compute gradients of the loss with respect to each weight, then updates weights using gradient descent:

```
weight = weight - learning_rate × gradient
```

## Key Architectures

### Convolutional Neural Networks (CNNs)

Designed for grid-like data (images, audio spectrograms).

- **Convolutional layer**: applies learnable filters to detect local features (edges, textures).
- **Pooling layer**: reduces spatial dimensions, adds translation invariance.
- **Fully connected layer**: combines features for final classification.

Used in: image classification, object detection, medical imaging.

### Recurrent Neural Networks (RNNs)

Designed for sequential data. The hidden state carries information across time steps.

- **LSTM (Long Short-Term Memory)**: uses gates to selectively remember/forget, solving the vanishing gradient problem.
- **GRU (Gated Recurrent Unit)**: simpler version of LSTM with fewer parameters.

Used in: time series forecasting, speech recognition (pre-Transformer era).

### Transformers

The dominant architecture since 2017. Uses self-attention to process all tokens in parallel.

- **Self-attention**: each position attends to all others, capturing long-range dependencies.
- **Multi-head attention**: runs multiple attention computations in parallel.
- **Positional encoding**: injects sequence order information since Transformers have no recurrence.

Used in: LLMs (GPT, Llama, Mistral), vision (ViT), speech (Whisper).

## Training Deep Networks

### Loss Functions

| Task | Loss function |
|---|---|
| Binary classification | Binary cross-entropy |
| Multi-class | Categorical cross-entropy |
| Regression | Mean squared error (MSE), Huber loss |

### Optimisers

| Optimiser | Notes |
|---|---|
| SGD | Simple, noisy; needs careful learning rate tuning |
| Adam | Adaptive learning rates; default for most tasks |
| AdamW | Adam + weight decay; preferred for Transformers |

### Regularisation

- **Dropout**: randomly zeroes neuron activations during training — prevents co-adaptation.
- **Batch normalisation**: normalises layer inputs — faster training, more stable gradients.
- **Weight decay (L2)**: penalises large weights in the loss function.
- **Data augmentation**: artificially expands training data (flips, crops, colour jitter for images).

### Learning Rate Schedules

- **Warmup + cosine decay**: warm up for a few thousand steps, then decay — standard for Transformer training.
- **ReduceLROnPlateau**: halve the LR when validation loss stops improving.

## Transfer Learning

Train on a large dataset (e.g., ImageNet, a large text corpus), then fine-tune on a smaller task-specific dataset.

- **Feature extraction**: freeze pretrained weights; only train the final layers.
- **Fine-tuning**: unfreeze some or all layers and continue training at a lower learning rate.
- **LoRA / QLoRA**: low-rank adapters that fine-tune a small number of extra parameters without modifying the base model — the dominant approach for LLM fine-tuning.

Transfer learning dramatically reduces data and compute requirements.
