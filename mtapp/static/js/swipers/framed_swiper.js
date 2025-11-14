document.addEventListener('DOMContentLoaded', function(){
    var framedSwiper = new Swiper('.framed-swiper-container', { // Options inside the {}
            slidesPerView: 1,
            spaceBetween: 60,
            loop: true,
            pagination: {
                el: ".swiper-pagination",
            },
            navigation: {
                nextEl:".swiper-button-next",
                prevEl:".swiper-button-prev",
            },
            breakpoints: {
                750: {
                    slidesPerView: 3,
                    spaceBetween: 20,
                },
            },
            autoplay: {
                delay: 3000,
                pauseOnMouseEnter: true,
            },

            speed: 2000,

            lazy: true,
            // lazyPreloaderClass:"swiper-lazy-preloader",
            // lazyPreloadPrevNext: 1,
    });
});
