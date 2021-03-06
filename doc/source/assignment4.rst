Assignment4
==============

This is my write-up for :download:`Assignment 4 <pdf/PSC585Ex4.pdf>`. 

Most of the code to implement this assignment is in
:py:class:`psc585.ps4.FinalModel`.  The attributes of this class includes
the data from ``FinalModel.mat`` and ``FinalData.mat`` provided with
the assignment.  

The method :py:meth:`~psc585.ps4.FinalModel.new_p` implements ``NewP``; 
:py:meth:`~psc585.ps4.FinalModel.phigprov` implements ``Phihprov``; 
:py:meth:`~psc585.ps4.FinalModel.ptilde` implements ``Ptilde``.

The Nested Pseudo Likelihood estimator described in part (d) is
implemented in the method :py:func:`~psc585.ps4.FinalModel.npl`.

The maximization of the partial pseudo-likelihood estimator in part
(e) is implemented in the method :py:meth:`~psc585.ps4.FinalModel.argmax_theta`.

First, I create a :py:class:`~psc585.ps4.FinalModel` object to hold
the data from the .mat files provided.

.. literalinclude:: ../../assignments/a4/a4.py
   :lines: 1-19

Then, I estimate :math:`\\\\theta` with nested pseudo-likelhood. 

.. literalinclude:: ../../assignments/a4/a4.py
   :lines: 22

The estimates for :math:`\\\\theta` are

::
   [ 0.00780143  0.59974144  1.95694046  0.29005511  0.26612347]

After 100 iterations, the relative residual was 2.71e-12.

