import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time



#def init():
    #ax.set_ylim(-1.1, 1.1)
    #ax.set_xlim(0,1)
    #line.set_data(x, y)
    #return line,

fig, ax = plt.subplots()
line, = ax.plot([], [], lw=2)
ax.grid()
x = []
y = []

t= 0
s=0

#init()




ax.set_ylim(-1.1, 1.1)
ax.set_xlim(0,1)
line.set_data(x, y)
plt.draw()


#plt.draw()
while(1):
    t = t + .01
    s = np.sin(t*10)
    x.append(t)
    y.append(s)

    xmin, xmax = ax.get_xlim()

    if t >= xmax:
        ax.set_xlim(t - (xmax - xmin), t )
        ax.figure.canvas.draw()
    line.set_data(x, y)

    plt.pause(.0001)
