#!/bin/tcsh -f
#
# Since number of original images in the DB are not balanced,
# we need to pick and choose images from fully augmented DB.
# This script does that
# Since doorframe has the largest number of images, for now, we are
# only reducing its size, leaving stair and curb untouched.

set filt = "00_BASE_IMAGE"
set augtypes = ( \
  00_noise_0.10	\
  00_noise_0.18	\
  #00_noise_0.23	\
  #00_noise_0.28	\
  01_blur1_gaussblur1	\
  #01_blur2_gaussblur2	\
  01_blur3_mblur_ver	\
  01_blur4_mblur_hor	\
  #01_blur5_mblur_rcnt	\
  #01_blur6_mblur_rshk1	\
  #01_blur7_mblur_rshk2	\
  02_sharp1	\
  02_sharp2	\
  #02_sharp3	\
  #02_sharp4	\
  #03_erode0	\
  #04_dilate0	\
  05_glow1	\
  #05_glow2	\
  #05_glow3	\
  #05_glow4	\
  #05_glow5	\
  06_rotate1	\
  06_rotate2	\
  #06_rotate3	\
  #06_rotate4	\
  07_perspective1	\
  07_perspective2	\
  #07_perspective3	\
  #07_perspective4	\
  #07_perspective5	\
  #07_perspective6	\
  08_scale1	\
  #08_scale2	\
  #08_scale3	\
  #08_scale4	\
  #09_pan1	\
  #09_pan2	\
  #09_pan3	\
  #09_pan4	\
)
#echo "Selected image aug types for doorframe: $augtypes"
if ( -d 'augmented') then
  echo "Directory 'augmented' already exists. Aborting"
  exit(1)
endif
if (! -d 'augmented.full') then
  echo "Directory 'augmented.full' doesn't exist. Aborting"
  exit(1)
endif

mkdir augmented
cd augmented
ln -s ../augmented.full/1_stair .
echo "Created link for augmented/1_stair/"
ln -s ../augmented.full/2_curb .
echo "Created link for augmented/2_curb/"
mkdir 3_doorframe
echo "Created directory augmented/3_doorframe/"
foreach t ( $augtypes )
  set filt = "$filt|$t"
end 
egrep "$filt" ../augmented.full/3_doorframe/labels.txt > 3_doorframe/labels.txt
cd 3_doorframe

echo "Creating links in augmented/3_doorframe/"
set linkscr = "./create_links.csh"
cat labels.txt | awk '{print "ln -s ../../augmented.full/3_doorframe/"$1" ."}' > $linkscr
chmod +x $linkscr
$linkscr
