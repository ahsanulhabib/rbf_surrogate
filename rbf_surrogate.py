import argparse
import numpy as np
import shelve
from scipy.spatial.distance import squareform, cdist, pdist


'''
Python Tool for Training RBF Surrogate Models

https://github.com/evanchodora/rbf_surrogate

Evan Chodora (2019)
echodor@clemson.edu

Can be used with a variety of RBFs (see the dictionary of function names below) and can be used with both
multi-dimensional inputs and multi-dimensional outputs (and scalars for both).

Makes use of the Spatial Distance calculation functions from SciPy to compute the radial distance matrices for the
radial basis function calculations.
(https://docs.scipy.org/doc/scipy/reference/spatial.distance.html)

Included RBFs:
 - Linear: "linear"
 - Cubic: "cubic"
 - Absolute Value: "absolute"
 - Multiquadratic: "multiquadratic"
 - Inverse Multiquadratic: "inverse_multiquadratic"
 - Gaussian: "gaussian"
 - Thin Plate: "thin_plate"

Program Usage:

rbf_surrogate.py [-h] -t {train,predict} [-x X_FILE] [-y Y_FILE] [-m MODEL_FILE] [-r RBF]

optional arguments:
  -h, --help                                    Show help message and exit.
  -t {train,predict}, --type {train,predict}    Specify whether the tool is to be used for training
                                                with "train" or making predictions with a stored model
                                                with "predict". (REQUIRED)
  -x X_FILE                                     Input file of x locations. (OPTIONAL) Default is "x_train.dat".
  -y Y_FILE                                     Output file for surrogate training. (OPTIONAL) Default is
                                                "y_train.dat".
  -m MODEL_FILE, --model MODEL_FILE             File to save the model output or use a previously
                                                trained model file. (OPTIONAL) Default is "model.db".
  -r RBF, --rbf RBF                             Specified RBF to use when training the surrogate. (OPTIONAL)
                                                Default is "gaussian".

'''


# Class to create or use an RBF surrogate model
class RBF:

    # Collection of possible Radial Basis Functions to use in the surrogate model:
    # Multiquadratic
    def _multiquadric(self, r):
        return np.sqrt(r ** 2 + self.epsilon ** 2)

    # Inverse Multiquadratic
    def _inverse_multiquadric(self, r):
        return 1.0 / np.sqrt(r ** 2 + self.epsilon ** 2)

    # Absolute value
    def _absolute_value(self, r):
        return np.abs(r)

    # Standard Gaussian
    def _gaussian(self, r):
        return np.exp(-(self.epsilon * r) ** 2)

    # Linear
    def _linear(self, r):
        return r

    # Cubic
    def _cubic(self, r):
        return (r ** 3)

    # Thin Plate
    def _thin_plate(self, r):
        return (r ** 2) * np.log(np.abs(r))

    # Function to compute the radial distance - r = (x-c)
    def _compute_r(self, a, b=None):
        if b is not None:
            # Return the distance matrix between two matrices (or vectors)
            # p=1: r = (x - c)
            # p=2: r = sqrt((x - c) ** 2) = ||x - c|| (Euclidean Norm)
            return cdist(a, b, 'minkowski', p=2)
        else:
            # Return a square matrix form of the the pairwise distance distance for the training locations
            # p=1: r = (x - c)
            # p=2: r = sqrt((x - c) ** 2) = ||x - c|| (Euclidean Norm)
            return squareform(pdist(a, 'minkowski', p=2))

    def _compute_N(self, r):

        # Dictionary object to store possible RBFs and associated functions to evaluate them
        # Can add as needed when a new function is added to the collection above
        rbf_dict = {
            "multiquadratic" : self._multiquadric,
            "inverse_multiquadratic" : self._inverse_multiquadric,
            "absolute": self._absolute_value,
            "gaussian" : self._gaussian,
            "linear" : self._linear,
            "cubic" : self._cubic,
            "thin_plate" : self._thin_plate
        }

        return rbf_dict[self.rbf_func](r)

    # Function to train an RBF surrogate using the suplied data and options
    def _train(self):
        r = self._compute_r(self.x_data)  # Compute the euclidean distance matrix
        N = self._compute_N(r)  # Compute the basis function matrix of the specified type
        self.weights = np.linalg.solve(N, self.y_data)  # Solve for the weights vector

    # Function to use a previously trained RBF surrogate for predicting at new x locations
    def _predict(self):
        r = self._compute_r(self.x_train, self.x_data)  # Compute the euclidean distance matrix
        N = self._compute_N(r)  # Compute the basis function matrix of the trained type
        self.y_pred = np.matmul(N.T, self.weights)  # Use the surrogate to predict new y values

    # Initialization for the RBF class
    # Defaults are specified for the options, required to pass in whether you are training or predicting
    def __init__(self, type, x_file='x_train.dat', y_file='y_train.dat', model_db='model.db', rbf_func='gaussian'):

        self.x_data = np.loadtxt(x_file, skiprows=1, delimiter=",")  # Read the input locations file
        self.x_data = self.x_data.reshape(self.x_data.shape[0], -1)  # Reshape into 2D matrix (avoids array issues)
        self.rbf_func = rbf_func  # Read user specified options (or the defaults)
        self.model_db = model_db  # Read user specified options (or the defaults)

        # Check for training or prediction
        if type == 'train':
            self.y_data = np.loadtxt(y_file, skiprows=1, delimiter=",")  # Read output data file
            self.y_data = self.y_data.reshape(self.y_data.shape[0], -1)  # Reshape into 2D matrix (avoids array issues)

            # Compute epsilon based on the standard deviation of the output values for the RBFs that use it
            self.epsilon = np.std(self.y_data)

            self._train()  # Run the model training function

            # Store model parameters in a Python shelve database
            model_data = shelve.open(model_db)
            model_data['rbf_func'] = self.rbf_func
            model_data['epsilon'] = self.epsilon
            model_data['x_train'] = self.x_data
            model_data['weights'] = self.weights
            print('\nSurrogate Data:')
            print('RBF Function: ', model_data['rbf_func'])
            print('Epsilon: ', model_data['epsilon'])
            print('Radial Basis Function Weights: ', '\n', model_data['weights'])
            print('\n', 'Trained surrogate stored in: ', self.model_db)
            model_data.close()

        else:
            # Read previously stored model data from the database
            model_data = shelve.open(model_db)
            self.rbf_func = model_data['rbf_func']
            self.epsilon = model_data['epsilon']
            self.x_train = model_data['x_train']
            self.weights = model_data['weights']

            model_data.close()

            print('\nUsing', self.model_db, 'to predict values...')
            self._predict()  # Run the model prediction function

            # Quick loop to add a header that matches the input file format
            y_head = []
            for i in range(self.y_pred.shape[1]):
                y_head.append('y' + str(i))

            # Convert header list of strings to a single string with commas and write out the predictions to a file
            header = ','.join(y_head)
            np.savetxt('y_pred.dat', self.y_pred, delimiter=',', fmt="%.6f", header=header, comments='')
            print('Predicted values stored in \"y_pred.dat\"')


# Code to run when called from the command line (usual behavior)
if __name__ == "__main__":

    # Parse the command line input options to "opt" variable when using on the command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--type', dest='type', choices=['train', 'predict'], required=True,
                        help="""Specify whether the tool is to be used for training with \"train\" or
                        making predictions with a stored model with \"predict\".""")
    parser.add_argument('-x', dest='x_file', default='x_train.dat',
                        help="""Input file of x locations. Default is \"x_train.dat\".""")
    parser.add_argument('-y', dest='y_file', default='y_train.dat',
                        help="""Output file for surrogate training. Default is \"y_train.dat\".""")
    parser.add_argument('-m', '--model', dest='model_file', default='model.db',
                        help="""File to save the model output or use a previously trained model file.
                        Default is \"model.db\".""")
    parser.add_argument('-r', '--rbf', dest='rbf', default='gaussian',
                        help="""Specified RBF to use when training the surrogate. Default is \"gaussian\".""")
    opts = parser.parse_args()

    # Create and run the RBF class object
    surrogate = RBF(opts.type, opts.x_file, opts.y_file, opts.model_file, opts.rbf)
