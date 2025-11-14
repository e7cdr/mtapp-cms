document.addEventListener('DOMContentLoaded', function(){
    
    var thumbSwiper2 = new Swiper('.thumb-swiper2-container', { // Options inside the {}
        slidesPerView: 'auto',
        spaceBetween: 10,
        freeMode: true,
        watchSlidesProgress: true,
        breakpoints: {
                750: {
                    slidesPerView: 3,
                    spaceBetween: 20,
                },
        }
        });

    var thumbSwiper1 = new Swiper('.thumb-swiper1-container', { // Options inside the {}
        spaceBetween: 10,
        loop: true,
        navigation: {
            nextEl: ".swiper-button-next",
            prevEl: ".swiper-button-prev",
        },
        thumbs: {
            swiper: thumbSwiper2,
        },
        autoplay: {
            waitForTransition: true,
            delay: 3000,
        },
        effect: 'fade',
        speed: 500,
        keyboard: {
            enabled: true,
            
        }
    });


});
