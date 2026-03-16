document.addEventListener('DOMContentLoaded', () => {
    const pctElement = document.getElementById('pct-value');
    const safetyStatus = document.getElementById('safety-status');
    const scramBtn = document.getElementById('scram-btn');
    
    let pct = 482.4;
    let isScrammed = false;

    // Simulate real-time data jitter
    setInterval(() => {
        if (isScrammed) return;

        const jitter = (Math.random() - 0.5) * 2;
        pct += jitter;
        
        pctElement.innerHTML = `${pct.toFixed(1)} <span class="metric-unit">°C</span>`;

        // Safety threshold checks
        if (pct > 1100) {
            safetyStatus.innerText = "Status: Critical";
            safetyStatus.style.borderColor = "#f85149";
            safetyStatus.style.color = "#f85149";
            safetyStatus.style.background = "rgba(248, 81, 73, 0.1)";
        } else if (pct > 900) {
            safetyStatus.innerText = "Status: Warning";
            safetyStatus.style.borderColor = "#d29922";
            safetyStatus.style.color = "#d29922";
            safetyStatus.style.background = "rgba(210, 153, 34, 0.1)";
        } else {
            safetyStatus.innerText = "Status: Nominal";
            safetyStatus.style.borderColor = "#238636";
            safetyStatus.style.color = "#238636";
            safetyStatus.style.background = "rgba(35, 134, 54, 0.1)";
        }
    }, 1000);

    scramBtn.addEventListener('click', () => {
        isScrammed = true;
        pct = 280.0; // Coolant drop
        pctElement.innerHTML = `${pct.toFixed(1)} <span class="metric-unit">°C</span>`;
        safetyStatus.innerText = "Status: SCRAM ACTIVE";
        safetyStatus.style.borderColor = "#f85149";
        safetyStatus.style.color = "#f85149";
        safetyStatus.style.background = "rgba(248, 81, 73, 0.1)";
        scramBtn.disabled = true;
        scramBtn.innerText = "SYSTEM HALTED";
        scramBtn.style.opacity = "0.5";
        
        console.log("🛑 Sovereign SCRAM initiated via HUD.");
    });
});
