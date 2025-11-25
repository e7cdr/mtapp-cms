document.addEventListener('DOMContentLoaded', function () {
    var fadeSwiper = new Swiper('.fade-swiper-container', {
     slidesPerView: 1,
     spaceBetween: 10,
     loop: true,
     pagination: {
      el: '.swiper-pagination',
      type: "progressBar",
     },
    effect: 'fade',
      fadeEffect: {
      crossFade: true
    },
     autoplay: {
      delay: 3000,
     },
     speed: 2000,
     lazy: true,
    });
});