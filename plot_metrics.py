import json
import matplotlib.pyplot as plt

# Load your results
with open('data/results.json', 'r') as f:
    results = json.load(f)

# Select metrics to plot
metrics = ['bleu', 'rouge1', 'rouge2', 'rougeL', 'precision', 'recall', 'f1', 'recall@k']
values = [results[m] for m in metrics]

# Create bar chart
plt.figure(figsize=(10, 6))
bars = plt.bar(metrics, values, color='skyblue')
plt.ylim(0, 100)
plt.ylabel('Score (%)')
plt.title('Evaluation Metrics for Bhartiyam')
plt.xticks(rotation=30)

# Annotate bars with values
for bar, value in zip(bars, values):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{value:.1f}', ha='center', va='bottom')

plt.tight_layout()
plt.show()
