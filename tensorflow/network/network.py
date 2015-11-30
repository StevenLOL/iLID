import tensorflow as tf
import os
from layer import *

class Network(object):
    def __init__(self, name, input_shape, output_shape, hidden_layers):
        self.name = name
        self.layers = None
        self.input_shape = input_shape
        self.output_shape = output_shape

        self.initialize_input()
        self.hidden_layers = hidden_layers

        self.build()

        self.training_set = None
        self.test_set = None
        self.cost = None
        self.optimizer = None
        self.log_path = None
        self.snapshot_path = None

    def initialize_input(self):
        self.x = tf.placeholder(tf.types.float32, [None] + self.input_shape)
        self.y = tf.placeholder(tf.types.float32, [None] + self.output_shape)
        self.append(InputLayer(self.x))
        
    def build(self):
        for hidden_layer in self.hidden_layers:
            self.append(hidden_layer)

        self.print_network()

    def append(self, layer):
        if self.layers:
            layer.connect(self.layers)
            self.layers = layer
        else:
            assert(layer.layer_type == "input")
            self.input_layer = layer
            self.layers = layer

        return self

    def print_network(self):
        def loop(layer):
            if layer.layer_type == "input":
                print layer.name, layer.out_shape.as_list()[1:]
            else:
                print layer.name, layer.in_shape.as_list()[1:], "->", layer.out_shape.as_list()[1:]
                loop(layer.previous_layer)
        loop(self.layers)

    def add_training_input(self, training_set, test_set):
        self.training_set = training_set
        self.test_set = test_set
        assert(training_set.input_shape == test_set.input_shape)
        assert(training_set.input_shape == self.input_shape)
        assert([training_set.num_labels] == self.output_shape)

    def add_prediction_input(self):
        pass

    def set_cost(self, logits_cost_function = tf.nn.softmax_cross_entropy_with_logits):
        #Last Layer should be softmax_linear
        assert(self.layers.layer_type == "softmax_linear")
        self.cost = tf.reduce_mean(logits_cost_function(self.layers.output, self.y))
        tf.scalar_summary("loss", self.cost)

    def set_optimizer(self, learning_rate, optimizer = tf.train.AdamOptimizer):
        self.optimizer = optimizer(learning_rate=learning_rate).minimize(self.cost)

    def set_accuracy(self):
        correct_pred = tf.equal(tf.argmax(self.layers.output, 1), tf.argmax(self.y, 1))
        self.accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.types.float32))
        tf.scalar_summary("accuracy", self.accuracy)

    def make_path(self, path):
        if not os.path.isdir(path):
            os.path.mkdir(path)

    def set_log_path(self, log_path):
        self.log_path = log_path
        self.make_path(log_path)

    def set_snapshot_path(self, snapshot_path):
        self.snapshot_path = snapshot_path
        self.make_path(snapshot_path)

    def run(self, batch_size, iterations, display_step = 100):
        init = tf.initialize_all_variables()
        self.merged_summary_op = tf.merge_all_summaries()

        with tf.Session() as sess:
            self.saver = tf.train.Saver()
            self.summary_writer = tf.train.SummaryWriter(self.log_path, sess.graph_def)
            sess.run(init)
            self.train(sess, batch_size, iterations, display_step)
            self.evaluate(sess, batch_size)

    def train(self, sess, batch_size, iterations, display_step):
            step = 0
            while step < iterations:
                batch_xs, batch_ys = self.training_set.next_batch(batch_size)
                sess.run(self.optimizer, feed_dict={self.x: batch_xs, self.y: batch_ys})

                if step % display_step == 0:
                    self.write_progress(sess, step, batch_size)

                step += 1

            print "Optimization Finished!"

    def write_progress(self, sess, step, batch_size):
        batch_xs, batch_ys = self.test_set.next_batch(batch_size)

        summary_str, acc, loss = sess.run([self.merged_summary_op, self.accuracy, self.cost], feed_dict={self.x: batch_xs, self.y: batch_ys})
        self.summary_writer.add_summary(summary_str, step)
        if self.snapshot_path:
            path = os.path.join(self.snapshot_path, self.name + ".tensormodel")
            self.saver.save(sess, path, global_step=step)
        print "Iter {0}, Loss= {1:.6f}, Training Accuracy= {2:.5f}".format(step, loss, acc)


    def evaluate(self, sess, batch_size):
        #Accuracy
        batch_xs, batch_ys = self.test_set.next_batch(batch_size)
        print "Accuracy:", sess.run(self.accuracy, feed_dict={self.x: batch_xs, self.y: batch_ys})