document.addEventListener("DOMContentLoaded", () => {
    const playBtn = document.getElementById("playBtn");
    const gameSection = document.getElementById("gameSection");
    const gameFrame = document.getElementById("gameFrame");
    const originalBtnText = playBtn.textContent;

    // Handle responsive iframe sizing
    const resizeGameFrame = () => {
        gameFrame.style.height = `${gameFrame.offsetWidth * (9/16)}px`;
    };

    // Initialize ResizeObserver for the game container
    const resizeObserver = new ResizeObserver(() => {
        resizeGameFrame();
    });

    playBtn.addEventListener("click", async () => {
        try {
            // Show loading state
            playBtn.textContent = "Loading...";
            playBtn.disabled = true;

            // Show game section
            gameSection.classList.remove("hidden");
            
            // Load game
            gameFrame.src = "gameindex.html";
            resizeObserver.observe(gameFrame);
            
            // Wait for frame to load
            await new Promise((resolve, reject) => {
                gameFrame.onload = resolve;
                gameFrame.onerror = () => reject(new Error("Game failed to load"));
            });

            // Focus and scroll into view
            gameFrame.focus();
            gameSection.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });

        } catch (error) {
            console.error("Game loading error:", error);
            gameSection.classList.add("hidden");
            playBtn.textContent = "Try Again";
            alert("Failed to load the game. Please check your connection and try again.");
        } finally {
            playBtn.disabled = false;
            playBtn.textContent = originalBtnText;
        }
    });

    // Initial resize
    window.addEventListener("load", resizeGameFrame);
    window.addEventListener("resize", resizeGameFrame);
});