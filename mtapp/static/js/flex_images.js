const destinations = [
    {name: 'Ecuador', image: 'cuenca.jpg'},
    {name: 'Amazonas', image: 'mountain.jpg'},
];

function renderFlexImages(dest, containerId) {
    const img_container = document.getElementById('image')

    if (!img_container) {
        console.error('Containers don\'t exist');
        return;
    }

    // Clear existing
    // img_container.innerHTML = ''; //This will ensure the flex-images-container is empty. <div id="flex-images-container" class="flex-images-container"></div>


    const numDest = destinations.length; //To count how many destinations there are
    console.log(`Rendering ${numDest} destinations`); // To print the number of rendering in the console

    // Loop to create images

    for (let i = 0; i < numDest; i++) { // For every iteration, +1 to i. numDest here is equal to 1 because destinations.length = 1 due to Ecuadpr
        const img = document.createElement('img'); //This will create <img>
        const imageCont = document.createElement(`div`)
        img.src = destinations[i].image; // .image is the url from const destinations
        img.alt = destinations[i].name; // .name is the url from const destinations
        img.classList.add('flex-image'); // this will add flex-image as the img's class

        imageCont.classList.add('image-cont', 'transparent-lines', `image-container-${[i]}`)
        imageCont.style.cssText = 
        'display: flex; width: stretch; position: relative; justify-content: end;'
        //this function will run based on the amount of destinations. If numDest is equal to 6, then the function will create 6 images for each (i)

        // Dynamic width: 100% / numDest >>> This means the first image will be 100 / 1 == 100% width. Two images will be 50% 50%, and so on
        // img.style.flexBasis = `calc(100% / ${numDest}`;
        
        const p = document.createElement('p');
        p.classList.add('caption')
        p.innerHTML = destinations[i].name
        p.style.position = 'absolute'

        const lines = document.createElement('div')
        lines.classList.add('lines')

        img_container.appendChild(imageCont); // <div id="flex-images-container" class="flex-images-container"> <img....> </div>
        imageCont.appendChild(img);
        imageCont.appendChild(lines);
        imageCont.appendChild(p); // <div id="flex-images-container" class="flex-images-container"> <img....> </div>
    
    }
}

renderFlexImages(destinations, 'image');

