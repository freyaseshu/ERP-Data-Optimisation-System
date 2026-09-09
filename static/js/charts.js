document.addEventListener("DOMContentLoaded", function() {
    // Dummy Data for charts (will be replaced by real API data later)
    
    // Bar Chart
    var ctx = document.getElementById("performanceChart");
    if(ctx) {
        var performanceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ["Query 1", "Query 2", "Query 3", "Query 4"],
                datasets: [{
                    label: "Before Optimization",
                    backgroundColor: "#e74a3b",
                    hoverBackgroundColor: "#e74a3b",
                    borderColor: "#e74a3b",
                    data: [150.2, 85.5, 310.1, 45.3],
                },
                {
                    label: "After Optimization",
                    backgroundColor: "#1cc88a",
                    hoverBackgroundColor: "#1cc88a",
                    borderColor: "#1cc88a",
                    data: [5.1, 10.2, 12.5, 2.1],
                }],
            },
            options: {
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Pie Chart
    var ctxPie = document.getElementById("optimizationPieChart");
    if(ctxPie) {
        var optimizationPieChart = new Chart(ctxPie, {
            type: 'doughnut',
            data: {
                labels: ["Unoptimized", "Optimized", "Indexed"],
                datasets: [{
                    data: [55, 30, 15],
                    backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc'],
                    hoverBackgroundColor: ['#2e59d9', '#17a673', '#2c9faf'],
                    hoverBorderColor: "rgba(234, 236, 244, 1)",
                }],
            },
            options: {
                maintainAspectRatio: false,
                cutout: '80%',
            },
        });
    }
});
