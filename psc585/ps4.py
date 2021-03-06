""" Problem Set 4 specific code"""
import os
from os import path

import pytave
import scipy as sp
from scipy import io
from scipy import linalg as la
from  rpy2 import robjects
import rpy2.robjects.numpy2ri
from rpy2.robjects.packages import importr

_MFILES = path.abspath(path.join(path.dirname(__file__), "..", "octave"))
pytave.addpath(_MFILES)

def _pp(i, a):
    """Column in Pp for ai"""
    return (i * 2) + a

def _logit(y, x, offset):
    """ Wrapper for logit used in FinalModel.argmax_theta """
    ## Uses R for the glm function. 
    stats = importr("stats")
    fmla = robjects.Formula('y ~ x - 1')
    env = fmla.environment
    env['y'] = robjects.IntVector(y)
    env['x'] =  robjects.r.matrix(robjects.FloatVector(x.flatten('F')),
                                  ncol=x.shape[1])
    results = stats.glm(fmla, family="binomial",
                        offset=robjects.FloatVector(offset))
    return sp.asarray(results.rx2('coefficients'))

class FinalModel(object):
    """ Province revolt game

    Attributes
    -----------------

    delta : float
        Discount factor of the government and provinces
    g1oversigma : float
        Parameter :math:`\sigma_g`
    k : int
        Number of provinces
    m : int
        Number of states that provinces can take, :math:`2^k`
    n : int
        Number of states, :math:`k 2^k`
    x : ndarray, shape (k, )
        Variable correlated with the wealth generated by each province
    y : ndarray, shape (k, )
        Variable correlated with the cost of war to each province
    wg : float
        Government war cost
    D : ndarray, shape (k, k)
        Matrix of distances between provinces
    S : ndarray, shape (n, k)
        transition matrix
    data : ndarray, shape (T, k + 2)
        Data, as in FinalData.mat. The first column records the state
        :math:`l, s`, enumerated according to the order of the
        coordinates. The last column contains the actions of the
        government. The :math:`k` middle columns contain the actions
        of the provinces.

    Notes
    ----------

    This class contains the data and functions to solve the game between
    the provinces and government described in assignment 4.

    """
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            self.__setattr__(k, v)

    _properties = ['delta',
                   'g1oversigma',
                   'k',
                   'm',
                   'n',
                   'x',
                   'y',
                   'wg',
                   'D',
                   'S']

    @classmethod
    def from_mat(cls, model, data):
        """ Instantiate class from .mat files

        Parameters
        -------------
        model : string
              Path to FinalModel.dat
        data : string
              Path to FinalData.mat

        Returns
        ---------
        obj : FinalModel
              Instance of the FinalModel class

        """
        final_model = io.loadmat(model, squeeze_me = True)['model']
        keys = final_model.dtype.names
        kwargs = {}
        for k in keys:
            kwargs[k] = final_model[[k]][0]
        for k in ['k', 'm', 'n']:
            kwargs[k] = int(kwargs[k])
        for k in ['delta', 'wg', 'g1oversigma']:
            kwargs[k] = float(kwargs[k])
        kwargs['S'] = kwargs['S'].astype(int)
        final_data = io.loadmat(data)['data']
        ## adjust (l, s) and a_g columns to 0-indexing
        final_data[:, 0] -= 1
        final_data[:, -1] -= 1
        kwargs['data'] = final_data.astype(int)
        return cls(**kwargs)

    def model(self):
        """Return model dict"""
        return dict((k, self.__getattribute__(k)) for k in self._properties)  

    def new_p(self, Pp, Pg, theta):
        """ Calculate transition probabilities

        Parameters
        --------------
        
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government
        theta : ndarray, shape (5, )
             Parameters

        Returns
        ---------
        Pp : ndarray, shape (n, k)
             New conditional choice probabilities for provinces
        Pg : ndarray, shape (n, 2 k)
             New conditional choice probabilities for the government

        Notes
        -----------

        Takes conditional choice probabilities :math:`P` and :math:`\theta`
        as an input and returns new conditional choice values.
        This is the mapping :math:`\Psi` in part (c) of the assignment.

        This is a wrapper for the matlab function **NewP**.
        
        """
        theta = sp.atleast_2d(theta)
        return pytave.feval(2, "NewP", Pp, Pg, theta, self.model())

    def phigprov(self, Pp, Pg, theta):
        """ Calculate transition probabilities

        Parameters
        ------------
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government
        theta : ndarray, shape (5, )
             Parameters

        Returns
        ---------
        V : ndarray
            Observable state values

        Notes
        -----------

        Takes conditional choice probabilities :math:`P` and :math:`\theta`
        as an input and returns values :math:`V^P`.
        This is the mapping :math:`\Phi` in part (b) of the assignment.

        This is a wrapper for the matlab function **Phigprov**.
        
        """
        theta = sp.atleast_2d(theta)
        return pytave.feval(1, "Phigprov", Pp, Pg, theta, self.model())[0]

    def ptilde(self, Pp, Pg):
        """ Calculate transition probabilities

        Parameters
        ------------
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government

        Returns
        ---------
        P : ndarray
            Transition probability matrix

        Notes
        -----------

        Takes conditional choice probabilities :math:`P` as an input and
        returns the transition matrix :math:`\\tilde{P}`.

        This is a wrapper for the matlab function **Ptilde**.
        
        """
        return pytave.feval(1, "Ptilde", Pp, Pg, self.model())[0]

    def ptilde_i(self, Pp, Pg, i, ai):
        """ Transition probabilities conditional on player i's action

        Parameters
        ------------
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government
        i : int, 1 to k
            Province 
        ai : int, bool
            Province i's action :math:`a_i`

        Returns
        ---------
        P : ndarray
            Transition probability matrix

        Notes
        ---------

        This method calculates :math:`\\tilde{P}^P_i(a_i)`, the
        transition matrix with probabilities :math:`\\tilde{p}^P_i(l', s' | l, s, a_i)`.

        This is calculated by taking the matrix Pp, and replacing the
        columns corresponding to player :math:`i`'s actions assuming that player :math:`i`
        plays action :math:`a_i`.  This new probability matrix is then used
        as an input to :py:func:`psc585.PS4.FinalModel.ptilde`.
        
        """
        Ppi = Pp.copy()
        Ppi[: , _pp(i, 0)] = float((1 - ai) % 2)   # =1 when ai=0, =1 when ai=1
        Ppi[: , _pp(i, 1)] = float((2 - ai) % 2)   # =1 when ai=1, =0, when ai=0
        P = self.ptilde(Ppi, Pg)
        return P

    def y_d(self):
        """ Data matrix Y_d

        Returns
        --------
        y : ndarray, shape (k*T, )
            Matrix :math:`Y_d`


        Notes
        ----------

        Calculates the :math:`k * T \times 1` matrix :math:`Y_d` in part (e) of
        the assignment. 

        """
        y = self.data[:, 1:-1].ravel("F")
        return y

    def Ei_ai(self, Pp, i, a):
        """ Calculate E_i^P(a_i)

        Parameters
        -----------
        i : int, 1 to k
            Province 
        a : int,
            Action. 0 or 1.

        Returns
        -----------
        Ei : ndarray, shape (n, )
             Values of :math:`E_i^P(a_i, l, s) in part (b)

        Notes
        ---------

        .. math::

           E_i^P(a_i, l, s) = - \log(P_i[ a_i | l, s])

        """
        ## Probably could be a separate function
        return -sp.log(Pp[:, _pp(i, a)])


    def Ei(self, Pp, i):
        """ Calculate E_i^P

        Parameters
        -------------
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces
        i : int, 1 to k
            Province 

        Returns
        -----------
        Ei : ndarray, shape (n, )
             Values of :math:`E_i^P(l, a)` in part (b)

        Notes
        ----------
        
        .. math::
                        
           E_i^P(l, s) = \sum_{a=0}^1 P_i[a | l, s] E_i^P(a, l, s)

        """
        E = sp.vstack((self.Ei_ai(Pp, i, a) for a in (0, 1))).T
        W = sp.vstack((Pp[:, _pp(i, a)] for a in (0, 1))).T
        return (E * W).sum(1)

    def Eg_ag(self, Pg, a):
        """ Calculate Z_g^P(a_g)
        """
        return -sp.log(Pg[:, a])

    def Eg(self, Pg):
        """ Calculate Z_g^P
        """
        E = sp.vstack((self.Eg_ag(Pg, a) for a in range(7))).T
        return (Pg * E).sum(1)

    def Zia(self, Pg, i, a):
        """ Calculate Z_i^P(a_i)

        Parameters
        -------------
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government
        i : int, 1 to k
            Province 
        a : int
            Action of player :math:`i`. 0 or 1.

        Returns
        -----------
        Z : ndarray, shape (n, 5)
            Values of :math:`Z_i^P(a_i, l, s)` in part (b)

        Notes
        --------

        .. math::

           Z_i^P(a_i, l, s) = (1, x_i, -(1 - s_i) - P_g(i | l, s), -P_g(i | l, s) y_i)

        if :math:`a_i = 1` and 0 if :math:`a_i = 0`.
        
        """
        if a :
            x = self.x[i]
            y = self.y[i]
            s = self.S[:, i]
            pg_i = Pg[:, i]
            Z = sp.ones((self.n, 5))
            Z[:, 1] = x
            Z[:, 2] = -(1 - s)
            Z[:, 3] = -pg_i
            Z[:, 4] = -pg_i * y
        else:
            Z = sp.zeros((self.n, 5))
        return Z

    def Zi(self, Pg, Pp, i):
        """ Calculate Z_i^P

        Parameters
        -------------
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces
        i : int, 1 to k
            Province 

        Returns
        -------------
        Z : ndarray, shape (n, 5)
            Values of :math:`Z_i^P` from part (b).

        Notes
        -------------

        .. math::

           Z_i^P = \sum_{a=0}^1 P_i[a | l, s] Z_i^P(a, l, s)
        
        """
        ## I can ignore Zia(Pg, i, 0) because it is always 0
        Z = self.Zia(Pg, i, 1) * Pp[:, _pp(i, 1)][:, sp.newaxis]
        return Z

    def Wi(self, Pp, Pg, i):
        """ Compute matrix W_i^P

        Parameters
        -------------
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces
        i : int, 1 to k
            Province 

        Returns
        ------------
        W : ndarray, shape (n, 5)
           Values of :math:`W_i^P`

        Notes
        -----------

        .. math::

           W_i^P = (Z^P_i(1) + \delta (\\tilde{P}^P_i(0) - \\tilde{P}^P_i(0))(I - \delta \\tilde{P}^P)^{-1} - Z^P_i)

        """
        Zi1 = self.Zia(Pg, i, 1)
        Z = self.Zi(Pg, Pp, i)
        Pi1 = self.ptilde_i(Pp, Pg, i, 1)
        Pi0 = self.ptilde_i(Pp, Pg, i, 0)
        idp_inv_Z = la.solve(sp.eye(self.n) - self.delta * self.ptilde(Pp, Pg), Z)
        dpp = self.delta * (Pi1 - Pi0)
        W = (Zi1 + self.delta * (Pi1 - Pi0).dot(idp_inv_Z))
        return W

    def initprob(self):
        """ Calculate initial conditional probabilities based on observed data

        Notes
        -------

        If state (l, s) is observed in the data, set the value of P to the observed
        probability conditional on that state.  If state (l, s) not observed
        in the data, set the probability for each action to the unconditional
        probability for that player.

        Suggested by Brenton.

        """
        _MIN = 0.01
        _MAX = 0.99
        T = self.data.shape[0]
        ## Actions of government in T x k matrix with binary entries
        ag = sp.zeros((T, self.k))
        ag[sp.r_[:T], self.data[:, -1]] = 1
        ## Unconditional average action for government
        meanPgls = ag.mean(0)
        ## Initial values of Pg
        Pg = meanPgls[:, sp.newaxis].repeat(self.n, axis=1).T
        ## Unconditional average action for provinces
        meanPpls = self.data[:, 1:-1].mean(0)
        ## Initial values of Pp
        Pp = meanPgls[:, sp.newaxis].repeat(self.n, axis=1).T
        ## If state (ls) observed in data
        ## set values of Pp and Pg to observed mean
        for ls in range(self.n):
            ## Which state
            isls = (self.data[:, 0] == ls)
            if isls.any():
                Pp[ls, ] = self.data[isls, 1:-1].mean(0)
                Pg[ls, ] = ag[isls, :].mean(0)
        ## I cannot have 0 or 1s in the initla values
        Pg = sp.maximum(sp.minimum(Pg, _MAX), _MIN)
        Pg /= Pg.sum(1)[:, sp.newaxis]
        Pp = sp.maximum(sp.minimum(Pp, _MAX), _MIN)
        Pp = sp.vstack((1 - Pp, Pp)).reshape((self.n, self.k * 2), order='F')
        return (Pp, Pg)

    def Ci(self, Pp, Pg, i):
        """ Compute matrix C_i^P

        Parameters
        -------------
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces
        i : int, 1 to k
            Province 

        Returns
        ------------
        C : ndarray, shape (n,)
            Values of :math:`C_i^P`

        Notes
        -----------

        .. math::

           C_i^P = \delta (\tilde{P}_i^P(1)  - \tilde{P}_i^P(0))(1 - \delta \tilde{P}^P)^{-1} E_i^P

        """
        E = self.Ei(Pp, i)
        idp_inv_E = la.solve(sp.eye(self.n) - self.delta * self.ptilde(Pp, Pg), E)
        Pi1 = self.ptilde_i(Pp, Pg, i, 1)
        Pi0 = self.ptilde_i(Pp, Pg, i, 0)
        C = self.delta * (Pi1 - Pi0).dot(idp_inv_E)
        return C

    def C_d(self, Pp, Pg):
        """ Compute matrix C_d

        Parameters
        -------------
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces

        Returns
        ------------
        C : ndarray, shape (n,)
            Values of :math:`C_d`

        Notes
        ---------

        .. math::

           C_d(i * T + t, :) = C_i^P(l^t, s^t)

        The matrix `C_d` stacks entries from `C_i^P` by
        province and state in the **data** property.


        """
        ls = self.data[:, 0]
        C = sp.concatenate([self.Ci(Pp, Pg, i)[ls]
                            for i in range(self.k)])
        return C

    def _C(self, Pp, Pg):
        """ Calculate C 
        """
        return sp.vstack([self.Ci(Pp, Pg, i)
                          for i in range(self.k)]).T

    def _W(self, Pp, Pg):
        """ Calculate W
        """
        W = sp.concatenate([self.Wi(Pp, Pg, i)
                            for i in range(self.k)], axis=1)
        return W

    def W_d(self, Pp, Pg):
        """ Calculate matrix W_d

        Parameters
        -------------
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces

        Returns
        ------------
        W : ndarray, shape (n,)
            Values of :math:`W_d`

        Notes
        ---------

        .. math::
        
            W_d(i * T + t, :) = W_i^P(l^t, s^t)

        The matrix `W_d` concatenates rows of `W_i^P` by
        province and state in the **data** property.

        """
        ls = self.data[:, 0]
        W = sp.concatenate([self.Wi(Pp, Pg, i)[ls, ]
                            for i in range(self.k)], axis=0)
        return W

    def argmax_theta(self, Pp, Pg):
        """ Maximize partial pseudo-likelihood of theta

        Parameters
        -------------
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces. Initial guess.
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government. Initial guess.

        Returns
        ---------
        theta : ndarray (5, 1)
            Parameter estimates

        Notes
        ---------

        Implements the partial pseudo-likelihood algorithm in part (e) of
        the assignment.
        
        """
        C = self.C_d(Pp, Pg)
        W = self.W_d(Pp, Pg)
        Y = self.y_d()
        theta = _logit(Y, W, C)[:, sp.newaxis]
        return theta

    def npl(self, Pp, Pg, tol = 1e-13, maxit=100, verbose=False):
        """ Nested-pseudo likelihood Estimator

        Parameters
        -------------
        Pp : ndarray, shape (n, k)
             Conditional choice probabilities for provinces. Initial guess.
        Pg : ndarray, shape (n, 2 k)
             Conditional choice probabilities for the government. Initial guess.
        tol : float, optional
             Convergence tolerance
        maxit : int, optional
             Maximum number of iterations
        verbose : bool, optional
             Print iterations

        Returns
        ----------
        theta : ndarray, shape (5, 1)
             Parameter estimates
        converge : bool
             Did the estimates converge?
        t : int
             Number of iterations
        relres : float
             Relative residual at the end of the iterations

        Notes
        -----------

        Implements part (d) of the assignement.

        """
        converge = False
        relres = sp.inf
        theta = sp.zeros((5, 1))
        for t in range(maxit):
            theta_old = theta.copy()
            # Step ii
            theta = self.argmax_theta(Pp, Pg)
            # Step iii
            Pp, Pg = self.new_p(Pp, Pg, theta)
            # check for convergence
            relres = la.norm(theta - theta_old)
            if verbose:
                print ("%d %f" % (t, relres))
                print theta.squeeze()
            if t > 0 and relres < tol:
                converge = True
                break
        return (theta, converge, t + 1, relres)
