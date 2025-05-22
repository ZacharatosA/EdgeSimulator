package DroneSim;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.network.DefaultNetworkModel;
import com.mechalikh.pureedgesim.network.NetworkLink;
import com.mechalikh.pureedgesim.network.TransferProgress;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters.TYPES;
import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode.LinkOrientation;
import com.mechalikh.pureedgesim.taskgenerator.Task;

import java.util.ArrayList;
import java.util.List;

public class DroneNetworkModel extends DefaultNetworkModel {

    public DroneNetworkModel(SimulationManager simulationManager) {
        super(simulationManager);
    }

    @Override
    public void send(ComputingNode from, ComputingNode to, Task task, double fileSize, TransferProgress.Type type) {
        // Special handling for drone -> GNB communication
        if (isDroneToGnbCommunication(from, to)) {
            handleDroneToGnbTransfer(from, to, task, fileSize, type);
        }
        // Special handling for GNB -> drone communication
        else if (isGnbToDroneCommunication(from, to)) {
            handleGnbToDroneTransfer(from, to, task, fileSize, type);
        }
        // For all other cases, use the default implementation
        else {
            super.send(from, to, task, fileSize, type);
        }
    }

    private boolean isDroneToGnbCommunication(ComputingNode from, ComputingNode to) {
        return from.getType() == TYPES.EDGE_DEVICE && to.getType() == TYPES.EDGE_DATACENTER;
    }

    private boolean isGnbToDroneCommunication(ComputingNode from, ComputingNode to) {
        return from.getType() == TYPES.EDGE_DATACENTER && to.getType() == TYPES.EDGE_DEVICE;
    }

    private void handleDroneToGnbTransfer(ComputingNode from, ComputingNode to, Task task, double fileSize, TransferProgress.Type type) {
        // List for nodes
        List<ComputingNode> vertexList = new ArrayList<>();
        // List for connections
        List<NetworkLink> edgeList = new ArrayList<>();
        
        // Direct connection drone -> GNB
        vertexList.addAll(List.of(from, to));
        edgeList.add(from.getCurrentLink(LinkOrientation.UP_LINK));
        
        startTransfer(edgeList, vertexList, task, fileSize, type);
    }

    private void handleGnbToDroneTransfer(ComputingNode from, ComputingNode to, Task task, double fileSize, TransferProgress.Type type) {
        List<ComputingNode> vertexList = new ArrayList<>();
        List<NetworkLink> edgeList = new ArrayList<>();
        
        // Direct connection GNB -> drone
        vertexList.addAll(List.of(from, to));
        edgeList.add(to.getCurrentLink(LinkOrientation.DOWN_LINK));
        
        startTransfer(edgeList, vertexList, task, fileSize, type);
    }

    private void startTransfer(List<NetworkLink> edgeList, List<ComputingNode> vertexList, Task task, double fileSize, TransferProgress.Type type) {
        if (!edgeList.isEmpty()) {
            edgeList.get(0).addTransfer(
                new TransferProgress(task, fileSize, type)
                    .setVertexList(vertexList)
                    .setEdgeList(edgeList));
        }
    }
} 