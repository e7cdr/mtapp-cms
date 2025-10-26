document.addEventListener('DOMContentLoaded', () => {
  const slider = document.querySelector('.slider');
  const slides = document.querySelectorAll('.slider img');
  const navLinks = document.querySelectorAll('.slider-nav a');
  let currentIndex = 0;
  let autoPlay;

  if (slides.length === 0) {
    console.error('No slides found. Check your HTML.');
    return;
  }

  // Set initial state
  function updateCarousel(index) {
    slider.style.transform = `translateX(-${index * 100}%)`;
    
    // Update active slide (optional: if you want to add .active class for styling)
    slides.forEach((slide, i) => slide.classList.toggle('active', i === index));
    navLinks.forEach((link, i) => link.classList.toggle('active', i === index));
    
    currentIndex = index;
  }

  // Stop autoplay on interaction
  function stopAutoPlay() {
    if (autoPlay) {
      clearInterval(autoPlay);
      autoPlay = null;
    }
  }

  // Start autoplay
  function startAutoPlay() {
    stopAutoPlay(); // Clear any existing
    autoPlay = setInterval(() => {
      updateCarousel((currentIndex + 1) % slides.length);
    }, 6000); // Change 3000ms to adjust speed
  }

  // Event listeners for nav clicks
  navLinks.forEach((link, index) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      updateCarousel(index);
      stopAutoPlay(); // Pause on click
      // Optionally restart after a delay: setTimeout(startAutoPlay, 5000);
    });
  });

  // Pause on hover
  const sliderWrapper = document.querySelector('.slider-wrapper');
  sliderWrapper.addEventListener('mouseenter', stopAutoPlay);
  sliderWrapper.addEventListener('mouseleave', startAutoPlay);

  // Optional: Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
      stopAutoPlay();
      updateCarousel(Math.max(0, currentIndex - 1));
    }
    if (e.key === 'ArrowRight') {
      stopAutoPlay();
      updateCarousel(Math.min(slides.length - 1, currentIndex + 1));
    }
  });

  // Initial setup
  updateCarousel(0);
  startAutoPlay(); // Enable autoplay
});