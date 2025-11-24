document.addEventListener('DOMContentLoaded', () => {
    const update = () => {
        document.querySelectorAll('.parallax-bg').forEach(bg => {
            const speed = parseFloat(bg.style.getPropertyValue('--parallax-speed')) || 0.4;
            const y = window.scrollY * speed;
            bg.style.transform = `translateY(${y}px)`;
        });
    };
    window.addEventListener('scroll', update);
    update();
});