import os
import csv
import matplotlib.pyplot as plt

def read_results(filename):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    results = {}
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return results
        
    with open(filepath, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            results[row['query_name']] = float(row['execution_time_ms'])
    return results

def compare_and_visualize():
    before = read_results("results_before.csv")
    after = read_results("results_after.csv")
    
    if not before or not after:
        print("Missing result files. Please run test_query_performance.py first.")
        return

    print(f"{'Query':<50} | {'Before (ms)':<12} | {'After (ms)':<11} | {'Improvement (%)':<15}")
    print("-" * 95)
    
    queries = []
    before_times = []
    after_times = []
    
    for query_name in before.keys():
        t_before = before[query_name]
        t_after = after.get(query_name, t_before)
        
        improvement = 0
        if t_before > 0:
            improvement = ((t_before - t_after) / t_before) * 100
            
        print(f"{query_name[:48]:<50} | {t_before:<12.2f} | {t_after:<11.2f} | {improvement:<14.2f}%")
        
        # Abbreviate query name for chart
        short_name = query_name.split(':')[0]
        queries.append(short_name)
        before_times.append(t_before)
        after_times.append(t_after)

    # PHASE 8: Visualization
    x = range(len(queries))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar([i - width/2 for i in x], before_times, width, label='Before', color='#d9534f')
    ax.bar([i + width/2 for i in x], after_times, width, label='After', color='#5cb85c')
    
    ax.set_ylabel('Execution Time (ms)')
    ax.set_title('Query Performance Comparison (Before vs After Optimization)')
    ax.set_xticks(x)
    ax.set_xticklabels(queries)
    ax.legend()
    
    # Save the plot
    output_png = os.path.join(os.path.dirname(__file__), '..', 'static', 'performance_comparison.png')
    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    plt.savefig(output_png)
    
    # Also save in tests directory as requested
    plt.savefig(os.path.join(os.path.dirname(__file__), 'performance_comparison.png'))
    
    print(f"\nVisualization saved to {output_png}")

if __name__ == "__main__":
    compare_and_visualize()
