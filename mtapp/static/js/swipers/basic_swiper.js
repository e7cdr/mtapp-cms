document.addEventListener('DOMContentLoaded', function(){var basicSwiper = new Swiper('.basic-swiper-container', { // Options inside the {}
        slidesPerView: 4,
        spaceBetween: 20,
        loop: true,
        pagination: {
            el: ".swiper-pagination",
        },
        // navigation: {
        //     nextEl:".swiper-button-next",
        //     prevEl:".swiper-button-prev",
        // },
        breakpoints: {
            750: {
                slidesPerView: 3,
                spaceBetween: 20,
            },

            350: {
                slidesPerView: 2,
                spaceBetween: 10,
            },

            200: {
                slidesPerView: 1,
                spaceBetween: 10,
            }
        },
        autoplay: {
            delay: 4000,
            pauseOnMouseEnter: true,
        },

        speed: 2000,

        lazy: true,
        // lazyPreloaderClass:"swiper-lazy-preloader",
        // lazyPreloadPrevNext: 1,
});});

