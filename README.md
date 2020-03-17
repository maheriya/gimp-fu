# gimp-fu
Gimp Scripts (python) for AeVA (http://www.vasuyantra.com/aeva). These are generic enough to be ported for other projects.
1. labelling images for object detection dataset (this is currently quite specific and limited to AeVA)
2. Image augmentation (this is highly generic)

I developed this to label the images for AeVA early on when opensource image labelling software was not readily available. At this point, image labeling suites are easily available and I don't recommend these scripts. However, these may still be useful for image augmentation especially for augmentations that can change image/bounding box dimensions.



To use scripts from this directory, create a soft link to the 'plug-ins' directory in ${HOME}/.gimp-{version}

%> cd ${HOME}/.gimp-<version>
%> ln -s <repo_path>/gimp-fu/plug-ins .


If Gimp is already running, close it and re-run it. A menu 'DVIA' will appear. Each entry corresponds to a script in plug-ins directory (as of now three menu entries)


## Specification for Gimp XCF Based Augmentation for Detection Dataset [March 2016]
To add more variations on top of original images, following transformations can be carried out:
	1. Rotation (up to 30 degrees)
	2. Perspective distortion (how much?)
	3. Resize (how much?)
	4. Shifts (pan)
	5. Salt-and-pepper noise
	6. Blur
	7. Sharpen
	8. Erode
	9. Dilate
	10. Soft-glow (light effects)

With four variations of ten transformations above, we get 4*10=40 extra images per one original image.

So, with 1000 images, we can get 41,000 (positive) images for training.

Gimp XCF Based Automated Image Dataset Augmentation
Creating ground truth data for the images is a manual task. However, once the initial manual work of creating ground truth is accomplished, we can fully automate the rest of the steps for augmenting the image set with aforementioned transformations. To do those transformations in a precise and sensible manner, we need to ensure that the RoI (region of interest) is clearly marked up in the image. The rest of the automation flow can then use this information to keep relevant information in the transformed images.

Gimp XCF image format supports two features that are extremely useful for storing such ground truth information for later automation of image augmentation: layers and parasites. 

Layers
Layers will allow us to graphically mark up the image for ground truth (bounding box or nearest point) on a layer specifically designated for the purpose. 

The idea is that during the manual step of creating the ground truth, we will use Gimp to graphically add the bounding box or a 'nearest point' on the image for each class on a specific layer. When the automation scales or rotates an image, for example, this graphical markup will also be scaled along with the image and as a result, once ground truth is marked up, further math is avoided and is freely transformed into the generated image (the scripts still need to extract this information from appropriate layers).

Similarly, the RoI will also be marked up on the image (this is not the tight bounding box – just the general area of interest that we intend to keep in the generated image as much as possible). When panning or rotation is done, the automation scripts will try to make sure that RoI is mostly kept intact in the generated images.

Parasites
Parasites are basically data embedded in the image. The Gimp API allows us to procedurally write or read such parasite data. We will use the parasites to store labels classification ground truth in the image. The secondary usage of the parasites will be to also store BB and nearest point information. This is an extra check to avoid user mistakes (the actual info will always be picked up from image layers for BB or nearest point).

Scripts for Creating Ground Truth
Even though ground truth has to be created manually, we need help in doing it efficiently in order to be able to handle hundreds of images.

We will need scripts for following tasks:
	• Convert a set of jpeg or png images into Gimp XCF images. XCF images will be our 'original database'. All information will be permanently stored in XCF images. Automation script/s doing augmentation will use these XCF images as input.
	• Open a set of images from a directory or a set of directories and let the user edit one image at a time (saving one image and closing it will cause another image to be opened automatically)
	• Scripts can automatically add specific layers based on directory names. For example, images stored in 'stair' directory will be automatically labelled for that class, and user will only have to enter the BB and/or nearest point after that.
	• For images that have multiple classes, users will manually add the information. This actions can be implemented as menu options that users can select. For example:
		○ Draw Region of Interest menu entry: This will create an appropriate layer (if not already existing) for RoI. The user will simply draw a rectangle on the image by dragging the mouse.
		○ Select Label menu entry: This will prompt the user to select the label or multiple labels from a predefined set of labels. These will be added as parasites in the XCF. Appropriate layers will also be created.
		○ Draw BB menu entry: This will prompt user to select a label. The user will simply draw a rectangle on the image by dragging the mouse. The script will store the top-left and bottom-right points as the image parasites.
		○ Define Nearest Point menu entry: This will prompt user to select a label. The user will simply click or double-click on the image with mouse to define the nearest point. This will be shown in the image graphically as a cross-hair. The script will store the point in the image as a parasite.
	• We will support multiple classes per image, but not multiple instances (there will be only one BB and/or nearest point per class)
	• Checks: Automation scripts should check for consistency: Since all data is entered in the XCF image as parasites, the scripts can check for consistency between parasites and also between parasites and graphical information. For example, if a class label (parasite) exists and a class layer (image layer info) doesn't, then is an error. Similarly, if a class layer exists but a BB and/or nearest point doesn't exist (in parasites), that is an error.
		
		
Image Dataset Augmentation Script
This script will read XCF image files and automatically perform transformations on original images to augment the image dataset. 
