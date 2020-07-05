import numpy as np
import os
import types
import tensorflow as tf
import tensorflow.keras as keras
import tensorflow_datasets as tfds

from keras.activations import softmax, relu
from keras import Sequential
from keras.layers import Conv2D, Flatten, Dense
from python_speech_features import *
from scipy.io import wavfile
from ASRModel import ASRModel

MODEL_DIR = 'model'
MODEL_NAME = 'model.h5'
RES_DIR = 'res'
JSON_DIR = 'json'


def gen_sample(data, k):
    for v in data:
        yield v[k]


class CNN(ASRModel):

    # constructor
    def __init__(self, model_id: str):
        print("CNN constructor")
        self.model_id = model_id

        # Create model
        model_path = os.path.join(MODEL_DIR, model_id, MODEL_NAME)
        if os.path.isfile(model_path):
            self.model = keras.models.load_model(model_path)
            self.model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        else:
            # this is a new model
            self.model = Sequential()

    def preprocess(self, audio):
        """
        from an input path, load the single audio and return preprocessed audio
        which will be the input of the net
        :param audio: input audio path to preprocess
        :return: the preprocessed audio, the model input
        """

        # print("CNN preprocess")
        if isinstance(audio, str) and os.path.isfile(audio):
            fs, data = wavfile.read(audio)
            data = np.array(audio, dtype=float)
            data /= np.max(np.abs(data))
            return mfcc(data, fs, winlen=0.025, winstep=0.01, nfilt=26, nfft=512, lowfreq=0, highfreq=None,
                        preemph=0.97,
                        winfunc=lambda x: np.ones((x,))).reshape((99, 13, 1))
        elif isinstance(audio, np.ndarray):
            data = np.array(audio, dtype=float)
            data /= np.max(np.abs(data))
            data = mfcc(data, 16000, winlen=0.025, winstep=0.01, nfilt=26, nfft=512, lowfreq=0, highfreq=None,
                        preemph=0.97, winfunc=lambda x: np.ones((x,)))
            return data.reshape((99, 13, 1))
        else:
            raise TypeError("Input audio can't be preprocessed, unsupported type: " + str(type(audio)))

    def preprocess_gen(self, audios):
        for data in audios:
            data = np.array(data, dtype=float)
            data /= np.max(np.abs(data))
            yield mfcc(data, 16000, winlen=0.025, winstep=0.01, nfilt=26, nfft=512, lowfreq=0, highfreq=None,
                       preemph=0.97,
                       winfunc=lambda x: np.ones((x,))).reshape((99, 13, 1))

    def gen_validation(self, mnist_val, k_list):
        for sample in mnist_val:
            batch = sample[k_list[0]]
            labels = sample[k_list[1]]
            preprocessed_batch = np.array([self.preprocess(data) for data in batch])
            preprocessed_label = np.array(
                [np.concatenate((np.zeros(l), np.array([1.0]), np.zeros(11 - l))) for l in labels])
            yield preprocessed_batch, preprocessed_label

    def build_model(self):
        """
        Create the model structure with the parameters specified in the constructor
        :return:
        """
        # Parameters lists
        my_optimizers = [keras.optimizers.Adam(),  # Classic ADAM optimizer
                         keras.optimizers.Adadelta(),  # SGD method based on adaptive learning rate
                         keras.optimizers.SGD(nesterov=True)]  # SGD with momentum

        # add layers [! input shape must be (28,28,1) !]
        self.model.add(Conv2D(64, kernel_size=3, activation=relu, input_shape=(99, 13, 1)))
        self.model.add(Conv2D(32, kernel_size=3, activation=relu))
        self.model.add(Flatten())
        self.model.add(Dense(12, activation=softmax))
        self.model.compile(loss='categorical_crossentropy', optimizer=my_optimizers[0], metrics=['accuracy'])

        print("CNN build_model")

    def train(self, trainset):
        """
        Train the builded model in the input dataset specified in the
        :return: the id of the builded model, useful to get the .h5 file
        """

        if os.path.isdir(trainset):
            pass
        else:

            batch_size = 32
            epochs = 10

            ds_train, info_train = tfds.load('speech_commands', split=tfds.Split.TRAIN, batch_size=500, with_info=True)
            ds_val, info_val = tfds.load('speech_commands', split=tfds.Split.VALIDATION, batch_size=100, with_info=True)
            assert isinstance(ds_train, tf.data.Dataset)

            mnist_train = tfds.as_numpy(ds_train)
            mnist_val = tfds.as_numpy(ds_val)

            xy_train = self.gen_validation(mnist_train, ('audio', 'label'))
            xy_val = self.gen_validation(mnist_val, ('audio', 'label'))

            my_callbacks = [keras.callbacks.ReduceLROnPlateau(monitor="loss",
                                                              factor=0.1,
                                                              patience=2,
                                                              verbose=0,
                                                              mode="auto",
                                                              min_delta=1e-4,
                                                              cooldown=1,
                                                              min_lr=1e-3),
                            keras.callbacks.TerminateOnNaN(),
                            keras.callbacks.EarlyStopping(monitor="loss",
                                                          min_delta=1e-7,
                                                          patience=2,
                                                          verbose=0,
                                                          mode="auto")]

            self.model.fit(x=xy_train, epochs=epochs, verbose=2, steps_per_epoch=50, validation_steps=10,
                           validation_data=xy_val, callbacks=my_callbacks, use_multiprocessing=True)

        print("CNN train")

    @staticmethod
    def load_model(model_path: str) -> ASRModel:
        """
        load a pretrained model from the specified path
        :param model_path:
        :return:
        """
        if model_path.endswith(os.sep):  # support path ending with '/' or '\'
            model_path = model_path[:-1]
        assert os.path.isdir(model_path), "model_path is not a dir: {}".format(model_path)
        model_id = os.path.basename(model_path)
        print("CNN load_model {}".format(model_path))
        cnn = CNN(model_id)
        # cnn.graph = load_graph()  # "model.h5"
        return cnn

    def save_model(self, path: str):
        """
        Save the current model in the specified path
        :param path:
        :return:
        """

        # self.model.save(path, overwrite=True, include_optimizer=True, save_format=None, signatures=None, options=None)
        print("CNN save_model")

    def test(self, testset_path: str):
        """
        Test the trained model, with
        :return:
        """

        # self.model.predict(testset_path)
        print("CNN test")
