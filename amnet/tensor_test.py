import tensorflow as tf
import numpy as np
import amn as amnet
import atoms
from sklearn.decomposition import PCA
from tensorflow.examples.tutorials.mnist import input_data

reduced_dim = 50

# grab mnist data
mnist = input_data.read_data_sets("MNIST_data/", one_hot=True)
train_labels = mnist.train.labels
train_pca_images = []

pca = PCA()
pca.fit(mnist.train.images)

rotation = pca.components_
rotation_small = rotation[:reduced_dim]

for image in mnist.train.images:
    small_transformed_image = np.dot(rotation_small, image)
    train_pca_images.append(small_transformed_image)

test_labels = mnist.test.labels
test_pca_images = []

for image in mnist.test.images:
    small_transformed_image = np.dot(rotation_small, image)
    test_pca_images.append(small_transformed_image)


# hyperparameters
learning_rate = 0.5
epochs = 10
batch_size = 100

# declare the training data placeholders
# input x - for 28 x 28 pixels = 784
x = tf.placeholder(tf.float32, [None, reduced_dim])
# now declare the output data placeholder - 10 digits
y = tf.placeholder(tf.float32, [None, 10])

# declare the weights connecting the input to the hidden layer
w1 = tf.Variable(tf.random_normal([reduced_dim, 20], stddev=0.03), name='w1')
b1 = tf.Variable(tf.random_normal([20]), name='b1')
# and the weights connecting the hidden layer to the output layer
w2 = tf.Variable(tf.random_normal([20, 10], stddev=0.03), name='w2')
b2 = tf.Variable(tf.random_normal([10]), name='b2')

# calculate the output of the hidden layer
hidden_out = tf.add(tf.matmul(x, w1), b1)
hidden_out = tf.nn.relu(hidden_out)

# calculate the hidden layer output - in this case, let's use a softmax activated
# output layer
y_ = tf.nn.softmax(tf.add(tf.matmul(hidden_out, w2), b2))

# now let's define the cost function which we are going to train the model on
y_clipped = tf.clip_by_value(y_, 1e-10, 0.9999999)
cross_entropy = -tf.reduce_mean(tf.reduce_sum(y * tf.log(y_clipped)
                                              + (1 - y) * tf.log(1 - y_clipped), axis=1))

# add an optimiser
optimiser = tf.train.GradientDescentOptimizer(learning_rate=learning_rate).minimize(cross_entropy)

# finally setup the initialisation operator
init_op = tf.global_variables_initializer()

# define an accuracy assessment operation
correct_prediction = tf.equal(tf.argmax(y, 1), tf.argmax(y_, 1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))


# used to extract weights from tf network
def get_vars(var_set, sess):
    weights = []
    biass = []
    for v in var_set:
        if v.name[0] == 'w':
            weights.append(sess.run(v))
        elif v.name[0] == 'b':
            biass.append(sess.run(v))

    return weights, biass

# start the session
with tf.Session() as sess:
    # initialise the variables
    sess.run(init_op)
    total_batch = int(len(mnist.train.labels) / batch_size)
    for epoch in range(epochs):
        avg_cost = 0
        for i in range(total_batch):
            # batch_x, batch_y = mnist.train.next_batch(batch_size=batch_size)
            batch_x = train_pca_images[i*batch_size : (i+1)*batch_size]
            batch_y = train_labels[i*batch_size : (i+1)*batch_size]
            _, c = sess.run([optimiser, cross_entropy], feed_dict={x: batch_x, y: batch_y})
            avg_cost += c / total_batch
        print("Epoch:", (epoch + 1), "cost =", "{:.3f}".format(avg_cost))

    print("\nTraining complete!")
    print(sess.run(accuracy, feed_dict={x: test_pca_images, y: test_labels}))

    weights, biass = get_vars(tf.trainable_variables(), sess)



def make_relu_amn(weights, biass):
    dimensions = [weight.shape[0] for weight in weights]
    num_layers = len(dimensions)
    
    input_vars = amnet.Variable(dimensions[0])
    
    prev_layer_vars = input_vars
    num_relu = 0
    # compose each layer
    for n in range(num_layers):
        affine_edges = amnet.AffineTransformation(np.transpose(weights[n]), prev_layer_vars, biass[n])
        prev_layer_vars = atoms.make_relu(affine_edges)
        num_relu += affine_edges.outdim

    print(num_relu)
    return prev_layer_vars


# create ReLU AMN
nn = make_relu_amn(weights, biass)

# check if the network works properly
corrects = 0
totals = 0
for image, label in zip(test_pca_images[:1000], test_labels[:1000]):
    guess = nn.eval(image)
    guess_num = guess.tolist().index(max(guess.tolist()))
    actual_num = label.tolist().index(max(label.tolist()))
    if guess_num == actual_num:
        corrects += 1
    totals += 1

print('Correct classification of AMNet: ' + str(float(corrects)/float(totals)))
