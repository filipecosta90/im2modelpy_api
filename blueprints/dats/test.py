from dats import * 

def test_dat():
	status, arr2 = read_dat_file('data/tdmap_image_001_001.dat', 444, 444)
	plt.imshow(arr2, cmap=plt.get_cmap('gray') )
	plt.show()

def test_cv2():
	r = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
	datbin_as_bytes_array = r.hmget('10', ['bin'])
	if len( datbin_as_bytes_array ) > 0:
		datbin_as_bytes = datbin_as_bytes_array[0]
		datbin = np.array( pickle.loads(datbin_as_bytes) )
		plt.imshow(datbin, cmap=plt.get_cmap('gray') )
		plt.show()

test_cv2()