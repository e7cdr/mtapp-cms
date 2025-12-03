document.addEventListener('DOMContentLoaded', function(){
    var framedSwiper = new Swiper('.framed-swiper-container', { // Options inside the {}
            slidesPerView: 1,
            spaceBetween: 50,
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
                400: {
                    slidesPerView: 1,
                    spaceBetween: 10,
                },
            },
            autoplay: {
                delay: 2000,
            },        
            speed: 2000,
        lazy: true,
        // lazyPreloaderClass:"swiper-lazy-preloader",
        // lazyPreloadPrevNext: 1,
});
});