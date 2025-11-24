   document.addEventListener('DOMContentLoaded', function () {
    var coverflowSwiper = new Swiper('.coverflow-swiper-container', {
     slidesPerView: 2,
     spaceBetween: 10,
     loop: true,
     pagination: {
      el: '.swiper-pagination',
      type: "progressBar",
     },
   //   navigation: {
   //       nextEl:".swiper-button-next",
   //       prevEl:".swiper-button-prev",
   //   },
     breakpoints: {
      750: {
       slidesPerView: 3,
      },
      450: {
       slidesPerView: 2,
      },
     },
     effect: 'coverflow',
     autoplay: {
      delay: 4000,
     },
     speed: 3000,
     lazy: true,
    });
   });