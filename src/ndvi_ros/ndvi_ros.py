
# Start up ROS pieces.
# Ros libraries
PKG = 'ndvi_ros'
import roslib; roslib.load_manifest(PKG)
import rospy
import tf

# ROS messages.
from sensor_msgs.msg import CompressedImage
# We do not use cv_bridge it does not support CompressedImage in python
# from cv_bridge import CvBridge, CvBridgeError


# numpy and scipy
import numpy as np
from scipy.ndimage import filters

# OpenCV
import cv2





import time
import numpy as np

import cv2
import picamera
import picamera.array


def disp_multiple(im1=None, im2=None, im3=None, im4=None):
    """
    Combines four images for display.

    """
    height, width = im1.shape

    combined = np.zeros((2 * height, 2 * width, 3), dtype=np.uint8)

    combined[0:height, 0:width, :] = cv2.cvtColor(im1, cv2.COLOR_GRAY2RGB)
    combined[height:, 0:width, :] = cv2.cvtColor(im2, cv2.COLOR_GRAY2RGB)
    combined[0:height, width:, :] = cv2.cvtColor(im3, cv2.COLOR_GRAY2RGB)
    combined[height:, width:, :] = cv2.cvtColor(im4, cv2.COLOR_GRAY2RGB)

    return combined


def label(image, text):
    """
    Labels the given image with the given text
    """
    return cv2.putText(image, text, (0, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, 255)


def contrast_stretch(im):
    """
    Performs a simple contrast stretch of the given image, from 5-95%.
    """
    in_min = np.percentile(im, 5)
    in_max = np.percentile(im, 95)

    out_min = 0.0
    out_max = 255.0

    out = im - in_min
    out *= ((out_min - out_max) / (in_min - in_max))
    out += in_min

    return out


def run():
    with picamera.PiCamera() as camera:
        # Set the camera resolution
        x = 400
        camera.resolution = (int(1.33 * x), x)
        # Various optional camera settings below:
        # camera.framerate = 5
        # camera.awb_mode = 'off'
        # camera.awb_gains = (0.5, 0.5)

        # Need to sleep to give the camera time to get set up properly
        time.sleep(1)

        with picamera.array.PiRGBArray(camera) as stream:
            # Loop constantly
            while True:
                # Grab data from the camera, in colour format
                # NOTE: This comes in BGR rather than RGB, which is important
                # for later!
                camera.capture(stream, format='bgr', use_video_port=True)
                image = stream.array

                # Get the individual colour components of the image
                b, g, r = cv2.split(image)

                # Calculate the NDVI

                # Bottom of fraction
                bottom = (r.astype(float) + b.astype(float))
                bottom[bottom == 0] = 0.01  # Make sure we don't divide by zero!

                ndvi = (r.astype(float) - b) / bottom
                ndvi = contrast_stretch(ndvi)
                ndvi = ndvi.astype(np.uint8)

                # Do the labelling
                label(b, 'Blue')
                label(g, 'Green')
                label(r, 'NIR')
                label(ndvi, 'NDVI')

                # Combine ready for display
                combined = disp_multiple(b, g, r, ndvi)

                # Display
                cv2.imshow('image', combined)

                stream.truncate(0)

                # If we press ESC then break out of the loop
                c = cv2.waitKey(7) % 0x100
                if c == 27:
                    break
#--------------------------------------------------------------------------
					
class image_feature:

    def __init__(self):
        '''Initialize ros publisher, ros subscriber'''
        # topic where we publish
        self.image_pub = rospy.Publisher("/output/image_raw/compressed",
            CompressedImage)
        # self.bridge = CvBridge()

        # subscribed Topic
        self.subscriber = rospy.Subscriber("/camera/image/compressed",
            CompressedImage, self.callback,  queue_size = 1)
        if VERBOSE :
            print "subscribed to /camera/image/compressed"


    def callback(self, ros_data):
        '''Callback function of subscribed topic. 
        Here images get converted and features detected'''
        if VERBOSE :
            print 'received image of type: "%s"' % ros_data.format

        #### direct conversion to CV2 ####
        np_arr = np.fromstring(ros_data.data, np.uint8)
        image_np = cv2.imdecode(np_arr, cv2.CV_LOAD_IMAGE_COLOR)
        
        #### Feature detectors using CV2 #### 
        # "","Grid","Pyramid" + 
        # "FAST","GFTT","HARRIS","MSER","ORB","SIFT","STAR","SURF"
        method = "GridFAST"
        feat_det = cv2.FeatureDetector_create(method)
        time1 = time.time()

        # convert np image to grayscale
        featPoints = feat_det.detect(
            cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY))
        time2 = time.time()
        if VERBOSE :
            print '%s detector found: %s points in: %s sec.'%(method,
                len(featPoints),time2-time1)

        for featpoint in featPoints:
            x,y = featpoint.pt
            cv2.circle(image_np,(int(x),int(y)), 3, (0,0,255), -1)
        
        cv2.imshow('cv_img', image_np)
        cv2.waitKey(2)

        #### Create CompressedIamge ####
        msg = CompressedImage()
        msg.header.stamp = rospy.Time.now()
        msg.format = "jpeg"
        msg.data = np.array(cv2.imencode('.jpg', image_np)[1]).tostring()
        # Publish new image
        self.image_pub.publish(msg)
        
        #self.subscriber.unregister()
#--------------------------------------------------------------------------
					
					
					
					
					
					
					
					
					
    # Important cleanup here!
    cv2.destroyAllWindows()

if __name__ == '__main__':
    run()
