#!/bin/tcsh -f
#
# Since number of original images in the DB are not balanced,
# we need to pick and choose images from fully augmented DB.
# This script does that
# Pick *8 augmented from doorframe, and *22 from stair while keeping curb untouched.
# This should give approximately balanced augmented DB.

set augtypes_doorframe = ( \
  00_noise_0.10	\
  00_noise_0.18	\
  #00_noise_0.23	\
  #00_noise_0.28	\
    #01_blur1_gaussblur1	\
  #01_blur2_gaussblur2	\
  01_blur3_mblur_ver	\
    #01_blur4_mblur_hor	\
  #01_blur5_mblur_rcnt	\
  #01_blur6_mblur_rshk1	\
  #01_blur7_mblur_rshk2	\
    #02_sharp1	\
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
    #06_rotate2	\
  #06_rotate3	\
  #06_rotate4	\
  07_perspective1	\
    #07_perspective2	\
  #07_perspective3	\
  #07_perspective4	\
  #07_perspective5	\
  #07_perspective6	\
    #08_scale1	\
  #08_scale2	\
  #08_scale3	\
  #08_scale4	\
  #09_pan1	\
  #09_pan2	\
  #09_pan3	\
  #09_pan4	\
)

set augtypes_stair = ( \
  00_noise_0.10	\
  00_noise_0.18	\
  00_noise_0.23	\
  #00_noise_0.28	\
  01_blur1_gaussblur1	\
  #01_blur2_gaussblur2	\
  01_blur3_mblur_ver	\
  01_blur4_mblur_hor	\
  01_blur5_mblur_rcnt	\
  #01_blur6_mblur_rshk1	\
  #01_blur7_mblur_rshk2	\
  02_sharp1	\
  02_sharp2	\
  02_sharp3	\
  #02_sharp4	\
  #03_erode0	\
  04_dilate0	\
  05_glow1	\
  05_glow2	\
  05_glow3	\
  #05_glow4	\
  #05_glow5	\
  06_rotate1	\
  06_rotate2	\
  06_rotate3	\
  #06_rotate4	\
  07_perspective1	\
  07_perspective2	\
  #07_perspective3	\
  #07_perspective4	\
  #07_perspective5	\
  #07_perspective6	\
  08_scale1	\
  08_scale2	\
  #08_scale3	\
  #08_scale4	\
  #09_pan1	\
  #09_pan2	\
  #09_pan3	\
  #09_pan4	\
)
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
ln -s ../augmented.full/2_curb .
echo "Created link for augmented/2_curb/"


### Create Links in stair
mkdir 1_stair
echo "Created directory augmented/1_stair/"
set filt = "00_BASE_IMAGE"
foreach t ( $augtypes_stair )
  set filt = "$filt|$t"
end 
egrep "$filt" ../augmented.full/1_stair/labels.txt > 1_stair/labels.txt
cd 1_stair
set linkscr_stair = "./create_links_stair.csh"
cat labels.txt | awk '{print "ln -s ../../augmented.full/1_stair/"$1" ."}' > $linkscr_stair
chmod +x $linkscr_stair
echo "Creating links in augmented/1_stair/"
$linkscr_stair
cd -

### Create Links in doorframe
mkdir 3_doorframe
echo "Created directory augmented/3_doorframe/"
set filt = "00_BASE_IMAGE"
foreach t ( $augtypes_doorframe )
  set filt = "$filt|$t"
end 
egrep "$filt" ../augmented.full/3_doorframe/labels.txt > 3_doorframe/labels.txt
cd 3_doorframe
set linkscr_doorframe = "./create_links_doorframe.csh"
cat labels.txt | awk '{print "ln -s ../../augmented.full/3_doorframe/"$1" ."}' > $linkscr_doorframe
chmod +x $linkscr_doorframe
echo "Creating links in augmented/3_doorframe/"
$linkscr_doorframe
cd -


